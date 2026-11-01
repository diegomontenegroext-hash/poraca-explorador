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


ATTESTATION_SCHEMA = "poraca-e2e-integrity-attestation-v1"
REQUIRED_COUNTS = (
    "acceptedReceipts", "missingAcceptedReceipts", "orphanedObservationLinks",
    "orphanAcceptedEventRelations", "missingAcceptedRelationEventIds",
    "missingCanonicalIdentities", "approvedEventIds", "missingApprovedEventIds",
    "canonicalTotal", "canonicalFuture", "confirmedScheduledFuture",
    "canaryElAnimo", "protectionTriggers",
)


def certify(report: dict) -> tuple[str, int]:
    """L4 data-only gates. Never claim API/SSO/coverage PASS from DB counts."""
    orphans = report.get("orphanedCanonicalLinks")
    if orphans is None:
        return "NOT_CERTIFIED_MISSING_INTEGRITY_READBACK", 2
    audit = report.get("attestation")
    if not isinstance(audit, dict) or audit.get("schema") != ATTESTATION_SCHEMA:
        return "NOT_CERTIFIED_MISSING_RECEIPT_ATTESTATION", 2
    if audit.get("projectId") != EXPECTED[3] or audit.get("branchId") != EXPECTED[4]:
        return "NOT_CERTIFIED_WRONG_DATABASE_SCOPE", 2
    if any(type(audit.get(key)) is not int or audit[key] < 0 for key in REQUIRED_COUNTS):
        return "NOT_CERTIFIED_MALFORMED_RECEIPT_COUNTS", 2
    if (int(orphans) != audit["orphanedObservationLinks"]
            or int(report.get("futureCanonical") or 0) != audit["canonicalFuture"]
            or int(report.get("futureConfirmed") or 0) < audit["confirmedScheduledFuture"]):
        return "NOT_CERTIFIED_CONTRADICTORY_READBACK", 2
    if audit.get("checkpointSurvivalGuard") is not True or audit["protectionTriggers"] != 2:
        return "P0_CANONICAL_PROTECTION_MISSING", 2
    if (audit["missingAcceptedReceipts"] > 0
            or audit["missingApprovedEventIds"] > 0
            or audit["orphanedObservationLinks"] > 0
            or audit["orphanAcceptedEventRelations"] > 0):
        return "P0_CANONICAL_HISTORY_BROKEN", 2
    if audit["canaryElAnimo"] != 1:
        return "P0_CANARY_NOT_PRESENT", 2
    if audit["confirmedScheduledFuture"] == 0:
        return "P0_NO_CONFIRMED_FUTURE_EVENTS", 2
    if report.get("nextBlockingGate") != "authenticated_api_and_web_check":
        return "BLOCKED_" + str(report.get("nextBlockingGate") or "UNKNOWN").upper(), 2
    if audit.get("decision") != "DATA_INTEGRITY_PASS_HTTP_SSO_SEPARATE":
        return "NOT_CERTIFIED_ATTESTATION_DECISION_CONFLICT", 2
    return "DATA_INTEGRITY_PASS_HTTP_AND_SSO_NOT_VERIFIED", 0


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
                # Aggregated SECURITY DEFINER function exposes counts only:
                # the scoped role cannot SELECT checkpoint or editorial logs.
                cursor.execute("SELECT public.poraca_e2e_integrity_attestation_v1()")
                receipt_row = cursor.fetchone()
                report["attestation"] = receipt_row[0] if receipt_row else None
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
            "missingAcceptedReceipts": (report.get("attestation") or {}).get("missingAcceptedReceipts"),
            "missingApprovedEventIds": (report.get("attestation") or {}).get("missingApprovedEventIds"),
            "orphanAcceptedEventRelations": (report.get("attestation") or {}).get("orphanAcceptedEventRelations"),
            "missingAcceptedRelationEventIds": (report.get("attestation") or {}).get("missingAcceptedRelationEventIds"),
            "canaryElAnimo": (report.get("attestation") or {}).get("canaryElAnimo"),
            "protectionTriggers": (report.get("attestation") or {}).get("protectionTriggers"),
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
