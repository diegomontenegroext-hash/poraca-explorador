"""Read-only P0 gate v2 preflight, separate from admission and canonical writes."""
from pathlib import Path

SQL_FILE = Path(__file__).resolve().parents[1] / "sql" / "20261029_function_identity_preflight_v2.sql"

def query():
    sql=SQL_FILE.read_text(encoding="utf-8")
    if not sql.lstrip().startswith("-- P0 gate function-level preview v2. READ ONLY.") or "WITH raw AS (" not in sql:
        raise ValueError("unexpected SQL contract")
    return sql

def summarize(rows):
    """Rows are read-only Neon tuples, never approved sessions."""
    keys=["title","observed_date","observed_time","mapped_public_source_id","host_key",
          "evidence_rows","supporting_rows","unique_detail_urls","specific_rooms",
          "room_labels","detail_urls","v1_gate_states","canonical_by_original",
          "observation_by_original","canonical_by_identity","observation_by_identity",
          "other_hosts_same_original","canonical_same_host_clock","v2_preflight",
          "authorized_to_write","observation_other_clock","canonical_other_clock"]
    counts={}
    samples=[]
    for record in rows:
        item=dict(zip(keys,record))
        status=item["v2_preflight"]
        counts[status]=counts.get(status,0)+1
        if len(samples)<12 and (status=="REVIEW_ONE_FUNCTION_PENDING_GATE_AUTHORIZATION"
            or status.startswith("HOLD_CONFLICTING")):
            samples.append({"title":str(item["title"]),
                            "date":str(item["observed_date"]),
                            "time":str(item["observed_time"]),
                            "venue_host":str(item["host_key"]),
                            "decision":str(status),
                            "specific_rooms":int(item["specific_rooms"]),
                            "original_details":int(item["unique_detail_urls"])})
    return {"status":"read_only","function_groups":len(rows),
            "by_decision":dict(sorted(counts.items())),
            "review_candidates":counts.get("REVIEW_ONE_FUNCTION_PENDING_GATE_AUTHORIZATION",0),
            "samples":samples,
            "authorized_to_write":False,
            "note":"Preflight is NOT gate authorization; page URL, date/time, room, public identity and original must still be reviewed."}
