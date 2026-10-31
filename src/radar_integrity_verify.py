#!/usr/bin/env python3
"""Por Acá — certify data-chain integrity without acquisition, mutation or new scheduler.

This is a read-only DATA attestation, not proof of HTTP/SSO visibility or editorial
authorization. Reuse the existing Radar workflow's verify_only branch.
"""
from __future__ import annotations

import json
import os
import sys

from radar_end_to_end import SQL as E2E_SQL, assess as assess_end_to_end

EXPECTED = (
    "neondb", "poraca_definitivo_ingest", "poraca_definitivo_scope",
    "frosty-union-52906378", "br-mute-recipe-b4odj2bl",
)


def certify(report: dict) -> tuple[str, int]:
    """Keep every gate separate. Never call a SQL PASS full E2E certification."""
    orphans = report.get("orphanedCanonicalLinks")
    if orphans is None:
        return "NOT_CERTIFIED_MISSING_INTEGRITY_READBACK", 2
    if int(orphans) > 0:
        return "P0_BROKEN_CANONICAL_REFERENCES", 2
    if report.get("nextBlockingGate") != "authenticated_api_and_web_check":
        return "BLOCKED_" + str(report.get("nextBlockingGate") or "UNKNOWN").upper(), 2
    return "DATA_CHAIN_READY_HTTP_AND_SSO_NOT_VERIFIED", 0


def read(url: str) -> dict:
    import psycopg
    with psycopg.connect(url, connect_timeout=12) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("SET LOCAL ROLE poraca_definitivo_scope")
                cursor.execute("""
                    SELECT current_database(), session_user, current_user,
                      current_setting('neon.project_id',true),
                      current_setting('neon.branch_id',true)
                """)
                identity = tuple(cursor.fetchone())
                if identity != EXPECTED:
                    raise RuntimeError("E2E_IDENTITY_SCOPE_MISMATCH")
                cursor.execute("""
                    SELECT
                      has_table_privilege(current_user,'public.radar_agenda_events','SELECT'),
                      has_table_privilege(current_user,'public.radar_v3_source_observations','SELECT'),
                      has_table_privilege(current_user,'radar_definitivo.runs','SELECT'),
                      has_table_privilege(current_user,'radar_definitivo.listing_occurrences','SELECT'),
                      has_table_privilege(current_user,'radar_definitivo.sources','SELECT'),
                      has_table_privilege(current_user,'public.radar_agenda_events','INSERT,UPDATE,DELETE,TRUNCATE')
                """)
                grants = tuple(cursor.fetchone())
                if grants != (True, True, True, True, True, False):
                    raise RuntimeError("E2E_READONLY_PRIVILEGES_NOT_ENFORCED")
                cursor.execute(E2E_SQL)
                report = assess_end_to_end(cursor.fetchone())
    return report


def main() -> int:
    url = os.environ.get("NEON_RADAR_OPERATIONAL_DATABASE_URL")
    if not url:
        print("::error::E2E_DATABASE_SECRET_MISSING", file=sys.stderr)
        return 2
    try:
        report = read(url)
        decision, exit_code = certify(report)
        evidence = {
            "schema": "poraca-e2e-replay-readonly-v1",
            "decision": decision,
            "dbIdentity": {"database": EXPECTED[0], "role": EXPECTED[2],
                           "projectId": EXPECTED[3], "branchId": EXPECTED[4]},
            "radarRunId": report.get("runId"),
            "radarRunStatus": report.get("radarRunStatus"),
            "sourcesChecked": report.get("sourcesChecked"),
            "stagingFuture": report.get("radarFutureObservations"),
            "canonicalFuture": report.get("futureCanonical"),
            "confirmedFuture": report.get("futureConfirmed"),
            "orphanedCanonicalLinks": report.get("orphanedCanonicalLinks"),
            "nextBlockingGate": report.get("nextBlockingGate"),
            "httpApi": "NOT_CHECKED",
            "webSso": "NOT_CHECKED",
            "approvedEventsMissing": "NOT_CHECKED_ROLE_RESTRICTED",
            "publicationApproved": False,
            "writesPerformed": False,
        }
        print("PORACA_E2E_READONLY " + json.dumps(evidence, ensure_ascii=False), flush=True)
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
                out.write("\n### Certificación de datos independiente (solo lectura)\n")
                out.write("**{}** · huérfanos **{}** · futuro canon **{}** · staging **{}**.\n\n".format(
                    decision, evidence["orphanedCanonicalLinks"],
                    evidence["canonicalFuture"], evidence["stagingFuture"]))
                out.write("HTTP API y web privada SSO **NO VERIFICADOS**. No hubo altas ni escrituras.\n")
        if exit_code:
            print("::error::" + decision, file=sys.stderr, flush=True)
        return exit_code
    except Exception as exc:
        print("::error::E2E_VERIFY_UNAVAILABLE " + type(exc).__name__ +
              " (not a valid P0 data attestation)", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
