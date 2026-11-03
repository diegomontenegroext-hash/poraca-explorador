#!/usr/bin/env python3
"""O3: report seven NATURAL FULL runs after a proven source-policy cutover.

Read-only. Runs within existing Radar workflow, does not trigger ingestion,
mutate runs/source_checks, certify website visibility or approve editorial data.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from radar_security_identity import approved_operational_identity

ROOT=Path(__file__).resolve().parents[1]
SQL_FILE=ROOT/"sql/20261103_o3_seven_full_postcutover_READ_ONLY.sql"
EXPECTED=("neondb","poraca_definitivo_ingest","poraca_definitivo_scope",
          "frosty-union-52906378","br-mute-recipe-b4odj2bl")
SCHEMA="poraca-o3-seven-natural-full-postcutover-v1"
STRICT="STRICT_COMPLETE"


def assess(rows):
    if not isinstance(rows,list) or len(rows)>7:
        raise ValueError("O3_INVALID_WINDOW")
    ids=[r["run_id"] for r in rows]
    if len(ids)!=len(set(ids)):
        raise ValueError("O3_REPEATED_RUN_ID")
    if any(r["status"] not in ("complete","partial","failed","error")
           or r["o3_run_state"] not in ("STRICT_COMPLETE","PARTIAL_OR_UNCERTIFIED")
           or type(r["is_post_cutover"]) is not bool
           for r in rows):
        raise ValueError("O3_UNEXPECTED_RUN_STATUS")
    # Reject false green if SQL status claims success while its numbers differ.
    for r in rows:
        must_be_strict=(r["status"]=="complete"
                        and r["sources_selected"]>0
                        and r["persisted_checks"]==r["sources_selected"]
                        and r["failed_or_errored"]==0
                        and r["health_schema"]=="poraca-health-v2")
        if (r["o3_run_state"]==STRICT)!=must_be_strict:
            raise ValueError("O3_SQL_PYTHON_VERDICT_MISMATCH")
    post=[r for r in rows if r["is_post_cutover"]]
    strict=sum(r["o3_run_state"]==STRICT for r in post)
    eligible=len(post)>=7
    decision=("CANDIDATE_6_OF_7_FOR_SEPARATE_E2E_CERTIFICATION"
              if eligible and strict>=6 else
              "POST_CUTOVER_7_FULLS_FAIL"
              if eligible else "PENDING_POST_CUTOVER_FULL_RUNS")
    latest=rows[0] if rows else None
    return {
        "schema":SCHEMA,"decision":decision,"readOnly":True,
        "fullRunsInWindow":len(rows),"postCutoverFulls":len(post),
        "postCutoverStrictComplete":strict,
        "requiredPostCutoverFulls":7,"requiredStrictComplete":6,
        "latestRunId":latest["run_id"] if latest else None,
        "latestPersistedState":latest["status"] if latest else None,
        "latestStrictState":latest["o3_run_state"] if latest else None,
        "cases":[{
            "runId":r["run_id"],
            "startedAt":str(r["started_at"]),"postCutover":r["is_post_cutover"],
            "declared":r["status"],"strict":r["o3_run_state"],
            "selected":r["sources_selected"],"checked":r["persisted_checks"],
            "ok":r["sources_ok"],"indexOnly":r["sources_index_only"],
            "failed":r["failed_or_errored"],
            "negativeChecks":r["negative_checks"]
        } for r in rows],
        "noHistoricalStatusRewritten":True,"publicationApproved":False,
        "websiteSsoConfirmed":False
    }


def read_operational(database_url):
    import psycopg
    sql=SQL_FILE.read_text(encoding="utf-8")
    if not sql.lstrip().startswith("-- Por Acá / O3 /"):
        raise ValueError("O3_SQL_SOURCE_MISMATCH")
    with psycopg.connect(database_url,connect_timeout=12) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SET LOCAL ROLE poraca_definitivo_scope")
                cur.execute("""SELECT current_database(),session_user,current_user,
                    current_setting('neon.project_id',true),
                    current_setting('neon.branch_id',true)""")
                if not approved_operational_identity(cur,cur.fetchone(),EXPECTED):
                    raise RuntimeError("O3_OPERATIONAL_IDENTITY_NOT_LIMITED")
                cur.execute(sql)
                names=[col.name for col in cur.description]
                return [dict(zip(names,row)) for row in cur.fetchall()]


def markdown(report):
    lines=["","### O3 — últimas siete FULL reales (lectura posterior a cutover)","",
           "**{}**; no equiparar GitHub SUCCESS con FULL complete.".format(report["decision"]),
           "",
           "| Fulls post-cutover | Estrictamente completas | Umbral |",
           "|---:|---:|---:|",
           "| {} | {} | 6 de 7 |".format(
               report["postCutoverFulls"],report["postCutoverStrictComplete"]),
           "",
           "| Run | Estado almacenado | Estado estricto | Fuentes con error |",
           "|---|---|---|---:|"]
    for x in report["cases"]:
        lines.append("| `{}` | {} | {} | {} |".format(
            x["runId"],x["declared"],x["strict"],x["failed"]))
    lines.append("")
    lines.append("Sin modificación de histórico ni publicación. "
                 "Una ventana completa aún requiere revisión independiente de API y web SSO.")
    return "\n".join(lines)+"\n"


def main():
    url=os.getenv("NEON_RADAR_OPERATIONAL_DATABASE_URL")
    if not url:
        print("::error::O3_LIMITED_SECRET_MISSING",file=sys.stderr)
        return 2
    try:
        report=assess(read_operational(url))
        print("PORACA_O3_NATURAL_FULL_WINDOW "+json.dumps(report,ensure_ascii=False,default=str),flush=True)
        summary=os.getenv("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary,"a",encoding="utf-8") as out:
                out.write(markdown(report))
        return 0
    except Exception as e:
        print("::error::O3_WINDOW_READ_FAILED "+type(e).__name__,
              file=sys.stderr,flush=True)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
