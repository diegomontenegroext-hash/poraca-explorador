#!/usr/bin/env python3
"""F5 cross-scene source-outage rehearsal against real Neon history, read-only.

Injects an outage in a SHADOW projection: it removes the largest source ROOT
hostname and inspects surviving provenance. Does NOT fail network sources,
change their status, fetch pages, claim recovery of the SAME event or publish.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from radar_security_identity import approved_operational_identity

ROOT=Path(__file__).resolve().parents[1]
SQL_FILE=ROOT/"sql/20261103_f5_shadow_loss_by_scene_READ_ONLY.sql"
SCHEMA="poraca-f5-shadow-independent-origin-v1"
# Four distinct program scenes. 'teatro_y_musica' is a useful bonus, NOT a
# fifth independent scene just because the DB gives it another circuit label.
SCENES=("arte_y_cultura","musica","teatro","literatura")
EXPECTED=("neondb","poraca_definitivo_ingest","poraca_definitivo_scope",
          "frosty-union-52906378","br-mute-recipe-b4odj2bl")
STRONG="SHADOW_PRECISE_COVERAGE_REMAINS"
PARTIAL="SHADOW_LEADS_ONLY_NOT_ORIGINAL_RECOVERY"
NONE="SHADOW_NO_CONTINUITY"


def assess(rows):
    if not isinstance(rows,list):
        raise ValueError("F5_INVALID_READBACK")
    by_scene={}
    for item in rows:
        scene=item.get("circuit")
        if not isinstance(scene,str) or not scene or scene in by_scene:
            raise ValueError("F5_DUPLICATED_OR_INVALID_SCENE")
        by_scene[scene]=item
        expected=(STRONG if item["removed_precise"]>0 and
                  item["remaining_precise_domains"]>0 else
                  PARTIAL if item["remaining_dated_leads"]>0 else NONE)
        if item["simulated_result"]!=expected:
            raise ValueError("F5_FALSE_GREEN_RESULT")
        if (item["actual_outage_verified"] or item["same_event_recovered"] or
                item["editorial_approved"] or item["f5_certified"]):
            raise ValueError("F5_SIMULATION_CANNOT_PUBLISH_OR_CERTIFY")
        alternatives=item["alternatives"]
        if not isinstance(alternatives,list):
            raise ValueError("F5_INVALID_ALTERNATIVES")
        roots=[x["root"] for x in alternatives]
        if len(roots)!=len(set(roots)) or item["removed_root"] in roots:
            raise ValueError("F5_SAME_HOST_IS_NOT_FALLBACK")
        if len(roots)!=item["remaining_domains"]:
            raise ValueError("F5_WRONG_INDEPENDENT_HOST_COUNT")
        if sum(x["precise"] for x in alternatives)!=item["remaining_precise_sessions"]:
            raise ValueError("F5_WRONG_SESSION_COUNT")
        if sum(x["datedLeads"] for x in alternatives)!=item["remaining_dated_leads"]:
            raise ValueError("F5_WRONG_LEAD_COUNT")
        for evidence in alternatives:
            if not isinstance(evidence["proof"],str) or not evidence["proof"].startswith("https://"):
                raise ValueError("F5_MISSING_ORIGINAL_OR_LEAD_PROOF")
    strong=[s for s in SCENES if by_scene.get(s,{}).get("simulated_result")==STRONG]
    limited=[s for s in SCENES if by_scene.get(s,{}).get("simulated_result")==PARTIAL]
    absent=[s for s in SCENES if by_scene.get(s,{}).get("simulated_result")==NONE or s not in by_scene]
    return {
        "schema":SCHEMA,"readOnly":True,"actualFaultInjected":False,
        "gate":"F5","gateStatus":"NOT_CHECKED",
        "fourDistinctSceneTarget":list(SCENES),
        "fourSceneShadowStrong":len(strong),
        "fourSceneShadowPartial":len(limited),
        "fourSceneNoContinuity":len(absent),
        "strongScenes":strong,"partialScenes":limited,"uncoveredScenes":absent,
        "compositeCircuitNotExtraIndependentScene":(
          by_scene.get("teatro_y_musica",{}).get("simulated_result")==STRONG),
        "reportedCircuits":len(rows),
        "outcomes":[{
            "circuit":x["circuit"],"removedRoot":x["removed_root"],
            "remainingPrecise":x["remaining_precise_sessions"],
            "remainingLeads":x["remaining_dated_leads"],
            "survivingRoots":[v["root"] for v in x["alternatives"]],
            "simulation":x["simulated_result"]
        } for x in rows],
        "sameEventRecovered":False,"publicationApproved":False,
        "noSourceChanges":True,
        "nextProof":"Real source-failure exercise, original readback in four unrelated scenes; no mere index, shared host or duplicate monitor."
    }


def read_operational(db_url):
    import psycopg
    sql=SQL_FILE.read_text(encoding="utf-8")
    if not sql.lstrip().startswith("-- F5 / 2026-11-03 / READ ONLY"):
        raise ValueError("F5_SQL_SOURCE_MISMATCH")
    with psycopg.connect(db_url,connect_timeout=12) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SET LOCAL ROLE poraca_definitivo_scope")
                cur.execute("""SELECT current_database(),session_user,current_user,
                    current_setting('neon.project_id',true),
                    current_setting('neon.branch_id',true)""")
                if not approved_operational_identity(cur,cur.fetchone(),EXPECTED):
                    raise RuntimeError("F5_OPERATIONAL_IDENTITY_NOT_LIMITED")
                cur.execute(sql)
                names=[col.name for col in cur.description]
                return [dict(zip(names,row)) for row in cur.fetchall()]


def markdown(data):
    lines=["","### F5 · Ensayo de pérdida virtual del origen más productivo",
           "","**F5 NOT_CHECKED**. Una proyección de cobertura no reproduce "
           "un fallo de red ni comprueba la misma función en otro origen.",
           "","| Escenas de programa con fuente alternativa precisa | Parciales | Sin respaldo |",
           "|---:|---:|---:|",
           f"| {data['fourSceneShadowStrong']}/4 | {data['fourSceneShadowPartial']} | {data['fourSceneNoContinuity']} |",
           "",
           "| Circuito | Origen retirado virtualmente | Precisas supervivientes | Pistas solamente |",
           "|---|---|---:|---:|"]
    for x in data["outcomes"]:
        lines.append("| {} | {} | {} | {} |".format(x["circuit"],
          x["removedRoot"],x["remainingPrecise"],x["remainingLeads"]))
    lines.extend(["","No escribir en Neon, no deshabilitar fuentes, no declarar F5 PASS por un dominio diferente.", ""])
    return "\n".join(lines)


def main():
    url=os.getenv("NEON_RADAR_OPERATIONAL_DATABASE_URL")
    if not url:
        print("::error::F5_LIMITED_SECRET_MISSING",file=sys.stderr)
        return 2
    try:
        report=assess(read_operational(url))
        print("PORACA_F5_SHADOW_RECOVERY "+json.dumps(report,ensure_ascii=False),flush=True)
        summary=os.getenv("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary,"a",encoding="utf-8") as f:
                f.write(markdown(report))
        return 0
    except Exception as e:
        print("::error::F5_SHADOW_FAILED "+type(e).__name__,file=sys.stderr,flush=True)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
