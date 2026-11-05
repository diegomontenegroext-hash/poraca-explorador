#!/usr/bin/env python3
"""One-off Radar 2 GitHub Actions pilot; never a new Radar or production scheduler.

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

def main():
    run_id = "radar2-ghpilot-" + os.environ["GITHUB_RUN_ID"]
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
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
                stream.write("## Radar 2 pilot — GitHub Actions\n\n")
                stream.write("Run: `" + run_id + "`. "
                             "Sources: " + ", ".join(sorted(origins)) +
                             ". Processed proposals: " + str(len(proposals)) +
                             " (not necessarily new). Neon same-run readback: " +
                             str(report["proposals_readback"]) + ".\n\n")
                stream.write("**Not yet certified:** independent new discoveries, "
                             "Vercel SSO API, scheduled continuity, direct Instagram.\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("RADAR2_PILOT_BLOCKED: " + type(exc).__name__ + " " + str(exc),
              file=sys.stderr)
        sys.exit(1)
