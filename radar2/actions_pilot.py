#!/usr/bin/env python3
"""Radar 2 acquisition on the existing workflow: daily or explicit manual check.

Uses the collector, reconciler and restricted writer already in radar2/.
No Instagram HTML, no ChatGPT search tool, no admission of canonicals.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from persist import execute

PROJECT = "frosty-union-52906378"
BRANCH = "br-mute-recipe-b4odj2bl"
ROLE = "poraca_radar_limited_prod"
ORIGINS = {"agendalaplata.ar", "teatrocerca.com.ar", "0221.com.ar",
           "eldia.com", "evento-simple.com", "alternativateatral.com",
           "circusproduce.com", "casadionisio.com.ar",
           "residenciacorazon.com.ar", "dynamoteatro.com"}
ROOT = Path(__file__).resolve().parent.parent

# Mirrors the EXISTING radar2.private_discoveries ranking, without requiring
# SELECT privileges on that read-only API view. The limited Radar writer only
# has SELECT on radar2.proposals. No migrations, new grants or canonical edits.
NEW_DISCOVERY_METRICS_SQL = """
WITH ranked AS (
 SELECT p.proposal_id,p.last_run_id,p.first_seen_at,
 ROW_NUMBER() OVER (
  PARTITION BY lower(regexp_replace(p.title,'[^[:alnum:]]','','g')),
    p.event_date,p.event_time,
    lower(regexp_replace(coalesce(p.venue,''),'[^[:alnum:]]','','g'))
  ORDER BY CASE WHEN p.review_state='fuente_original' THEN 0 ELSE 1 END,
    p.first_seen_at,p.proposal_id
 ) AS rn
 FROM radar2.proposals p
 WHERE coalesce(p.evidence->>'duplicate_of','')=''
)
SELECT
 (SELECT count(*) FROM radar2.proposals
  WHERE last_run_id=$1 AND first_seen_at >= $2::timestamptz) AS new_ids,
 (SELECT count(*) FROM ranked
  WHERE rn=1 AND last_run_id=$1 AND first_seen_at >= $2::timestamptz)
  AS new_visible_unique
"""

def main():
    run_id = ("radar2-ghdaily-" if os.environ.get("GITHUB_EVENT_NAME") == "schedule" else "radar2-ghpilot-") + os.environ["GITHUB_RUN_ID"]
    connection = os.environ.get("NEON_RADAR_LIMITED_DATABASE_URL", "")
    if not connection:
        raise RuntimeError("MISSING_LIMITED_NEON_SECRET")
    if not (urlsplit(connection).hostname or "").endswith(".neon.tech"):
        raise RuntimeError("NOT_NEON_ENDPOINT")

    # Preflight happens before opening external sources or touching persistent data.
    identification = execute(connection,
        "SELECT current_user AS role, current_setting('neon.project_id',true) AS project, "
        "current_setting('neon.branch_id',true) AS branch, "
        "has_table_privilege(current_user,'radar2.proposals','INSERT') AS can_write")
    row = identification.get("rows", [{}])[0]
    if (row.get("role"), row.get("project"), row.get("branch")) != (ROLE, PROJECT, BRANCH):
        raise RuntimeError("LIMITED_WRITER_IDENTITY_FENCE")
    if row.get("can_write") not in ("t", True):
        raise RuntimeError("LIMITED_WRITER_MISSING_PERMISSION")
    if execute(connection, "SELECT run_id FROM radar2.runs WHERE run_id=$1", [run_id]).get("rows"):
        raise RuntimeError("RUN_ID_ALREADY_EXISTS_NO_REPLAY")
    # Database clock avoids miscounting first_seen_at with the runner's clock.
    started_at = execute(connection,
        "SELECT clock_timestamp()::text AS started_at").get("rows", [{}])[0]["started_at"]

    with tempfile.TemporaryDirectory(prefix="radar2-gh-") as temp:
        work = Path(temp)
        cfg = work / "connection.json"
        cfg.write_text(json.dumps({"url": connection}))
        cfg.chmod(0o600)
        output = work / "acquired"
        output.mkdir()
        env = os.environ.copy()
        env["RADAR2_CONNECTION_FILE"] = str(cfg)
        cmd = [sys.executable, "radar2/collector.py", "--out", str(output),
               "--web", "--run-id", run_id]
        acquired = subprocess.run(cmd, cwd=ROOT, env=env,
                                  capture_output=True, text=True, timeout=1500)
        if acquired.returncode:
            raise RuntimeError("COLLECTOR_FAILED_" + str(acquired.returncode) +
                               " " + acquired.stderr[-450:])

        result = json.loads((output / "result.json").read_text())
        documents = result.get("documents", [])
        proposals = result.get("proposals", [])
        origins = set()
        for document in documents:
            host = (urlsplit(document.get("url", "")).hostname or "").lower()
            for origin in ORIGINS:
                if host == origin or host.endswith("." + origin):
                    origins.add(origin)
        errors = sum(bool(row.get("error")) for row in result.get("checks", []))
        print(json.dumps({"phase": "acquisition", "run_id": run_id,
            "source_origins": sorted(origins), "documents": len(documents),
            "proposals_processed_not_new": len(proposals), "source_errors": errors}))
        if len(origins) < 2 or not proposals:
            raise RuntimeError("SOURCE_COVERAGE_GATE_FAILED_NO_PERSISTENCE")

        persisted = subprocess.run([sys.executable, "radar2/persist.py",
                                    str(output / "result.json")],
                                   cwd=ROOT, env=env, capture_output=True,
                                   text=True, timeout=120)
        if persisted.returncode:
            raise RuntimeError("PERSISTENCE_FAILED_" + str(persisted.returncode) +
                               " " + persisted.stderr[-450:])
        # This control must read the SAME run back from Neon, not infer success
        # from a previous batch or GitHub's own job status.
        check = execute(connection,
            "SELECT (SELECT count(*) FROM radar2.proposals WHERE last_run_id=$1) "
            "AS proposals_readback, "
            "(SELECT summary->>'status' FROM radar2.runs WHERE run_id=$1) AS run_status",
            [run_id]).get("rows", [{}])[0]
        if check.get("run_status") != "completed" or int(check.get("proposals_readback") or 0) < 1:
            raise RuntimeError("SAME_RUN_NEON_READBACK_FAILED")
        report = {"phase": "restricted_neon_readback", "run_id": run_id,
                  "status": check["run_status"], "proposals_readback":
                  int(check["proposals_readback"]), "source_origins": sorted(origins)}
        print(json.dumps(report))
        # Technical observations, never automatically approved events. A single
        # performance can have observations in Genda and Genda Teatro. Count
        # unique proposals using the same exact-key ranking as the private view.
        # Metrics failure is reported separately; it cannot undo a valid write.
        metrics = None
        try:
            row = execute(connection, NEW_DISCOVERY_METRICS_SQL,
                          [run_id, started_at]).get("rows", [{}])[0]
            metrics = {"new_ids": int(row["new_ids"]),
                       "new_visible_unique": int(row["new_visible_unique"])}
            if not (0 <= metrics["new_visible_unique"] <= metrics["new_ids"]):
                raise ValueError("INCONSISTENT_UNIQUE_COUNTS")
            print(json.dumps({"phase": "new_discoveries", "run_id": run_id,
                              **metrics}))
            # Persist today's snapshot for continuity audits: subsequent runs
            # can update last_run_id, but must not change this historical count.
            try:
                saved = execute(connection,
                    "UPDATE radar2.runs SET summary=summary || "
                    "jsonb_build_object('discovery_metrics_v1',$2::jsonb) "
                    "WHERE run_id=$1 AND summary->>'status'='completed' "
                    "RETURNING run_id",
                    [run_id, json.dumps(metrics)]).get("rows", [])
                if len(saved) != 1:
                    raise RuntimeError("RUN_SUMMARY_NOT_UPDATED")
                print(json.dumps({"phase": "metrics_persistence",
                                  "status": "saved", "run_id": run_id}))
            except Exception as persist_exc:
                print(json.dumps({"phase": "metrics_persistence",
                                  "status": "METRICS_NOT_PERSISTED",
                                  "error": type(persist_exc).__name__}))
        except Exception as exc:
            print(json.dumps({"phase": "new_discoveries", "run_id": run_id,
                              "status": "METRICS_UNAVAILABLE",
                              "error": type(exc).__name__}))
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
                stream.write("## Radar 2 — GitHub Actions\n\n")
                stream.write("Run: `" + run_id + "`. "
                             "Sources: " + ", ".join(sorted(origins)) +
                             ". Processed proposals: " + str(len(proposals)) +
                             " (not necessarily new). Neon same-run readback: " +
                             str(report["proposals_readback"]) + ".\n\n")
                if metrics is not None:
                    stream.write("New IDs: " + str(metrics["new_ids"]) +
                                 ". **New unique visible proposals: " +
                                 str(metrics["new_visible_unique"]) +
                                 "** (including investigation documents; not "
                                 "necessarily confirmed events).\n\n")
                else:
                    stream.write("New/unique metrics: **unavailable**; check run logs.\n\n")
                stream.write("**Not yet certified:** Vercel SSO HTTP readback, "
                             "seven scheduled days, direct Instagram.\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("RADAR2_PILOT_BLOCKED: " + type(exc).__name__ + " " + str(exc),
              file=sys.stderr)
        sys.exit(1)
