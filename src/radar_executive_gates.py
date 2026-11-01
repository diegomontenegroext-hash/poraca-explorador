#!/usr/bin/env python3
"""Existing Radar workflow: independent executive SELECT-only scorecard; never publishes."""
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

EXPECTED = (
    "ORCHESTRATION", "RADAR_RECEIPT", "SOURCE_YIELD", "RUN_FUNNEL",
    "EDITORIAL_ADMISSION", "CANONICAL_INTEGRITY", "DIRECT_RADAR_AND_API_HTTP",
    "WEB_SSO_UX", "COVERAGE_BY_CIRCUIT", "LEAST_PRIVILEGE", "STABILITY",
)
STATES = {"PASS", "PARTIAL", "FAIL", "NOT_CHECKED"}
SQL_FILE = Path(__file__).resolve().parents[1] / "sql/20261101_executive_readiness_gates_READ_ONLY.sql"


def report_for(rows):
    """Never turn expected FAIL gates into an overall success."""
    indexed = {row["gate"]: row for row in rows}
    if len(rows) != len(EXPECTED) or set(indexed) != set(EXPECTED):
        raise ValueError("EXEC_GATE_MISSING_OR_DUPLICATED")
    if any(row["state"] not in STATES for row in rows):
        raise ValueError("EXEC_GATE_UNEXPECTED_STATE")
    counts = Counter(row["state"] for row in rows)
    return {
        "schema": "poraca-executive-readiness-v1",
        "readOnly": True, "autoPublished": False,
        "decision": "NOT_END_TO_END_CERTIFIED",
        "counts": {name: counts[name] for name in ("PASS", "PARTIAL", "FAIL", "NOT_CHECKED")},
        "runId": indexed["ORCHESTRATION"]["evidence"]["runId"],
        "gates": [{k: row[k] for k in ("gate", "state", "evidence", "acceptance", "next_action")}
                  for row in rows],
    }


def markdown(summary):
    def safe(s):
        return re.sub(r"[\r\n|<>]", " ", str(s or "")).strip()[:220]
    lines = [
        "", "## Por Acá — puertas ejecutivas (solo lectura)",
        "",
        "**Resultado global: NOT_END_TO_END_CERTIFIED.** Este reporte no aprueba eventos, "
        "no valida HTTP ni navegador SSO, y no convierte FAIL históricos en verde.",
        "",
        "Run: `{}` · PASS {} · PARTIAL {} · FAIL {} · NOT_CHECKED {}.".format(
            safe(summary["runId"]), *(summary["counts"][x] for x in
              ("PASS", "PARTIAL", "FAIL", "NOT_CHECKED"))),
        "",
        "| Puerta | Estado | Aceptación | Próximo paso |",
        "|---|---|---|---|",
    ]
    for g in summary["gates"]:
        lines.append("| {} | {} | {} | {} |".format(
            safe(g["gate"]),safe(g["state"]),safe(g["acceptance"]),safe(g["next_action"])))
    lines.append("")
    return "\n".join(lines)


def fetch_rows(database_url, sql):
    import psycopg
    with psycopg.connect(database_url, connect_timeout=12) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SET LOCAL ROLE poraca_definitivo_scope")
                cur.execute("""SELECT current_database(),session_user,current_user,
                    current_setting('neon.project_id',true),
                    current_setting('neon.branch_id',true)""")
                identity = cur.fetchone()
                if identity != ("neondb","poraca_definitivo_ingest",
                      "poraca_definitivo_scope","frosty-union-52906378",
                      "br-mute-recipe-b4odj2bl"):
                    raise RuntimeError("EXEC_GATE_OPERATIONAL_IDENTITY_MISMATCH")
                cur.execute(sql)
                cols = [item.name for item in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]


def main():
    database_url = os.getenv("NEON_RADAR_OPERATIONAL_DATABASE_URL")
    if not database_url:
        print("::error::EXEC_GATE_DATABASE_UNAVAILABLE", file=sys.stderr)
        return 2
    try:
        sql = SQL_FILE.read_text(encoding="utf-8")
        if "WITH latest AS (" not in sql or "DROP " in sql or "DELETE " in sql:
            raise ValueError("EXEC_GATE_SQL_FILE_UNEXPECTED")
        result = report_for(fetch_rows(database_url, sql))
        print("PORACA_EXECUTIVE_GATES " + json.dumps(result, ensure_ascii=False, default=str))
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as fp:
                fp.write(markdown(result))
    except Exception as exc:
        print("::error::EXEC_GATE_REPORT_NOT_VERIFIED " +
              type(exc).__name__ + ": " + str(exc)[:250], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
