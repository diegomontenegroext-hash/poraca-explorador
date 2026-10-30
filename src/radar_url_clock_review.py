"""Historical URL variants with conflicting clocks: report, never repair/merge."""
SQL = """WITH normalized AS (
 SELECT candidate_key,url,title,event_date,event_time,last_seen_at,
        regexp_replace(split_part(url,'#',1),'/+$','') AS url_key
 FROM radar_definitivo.candidates
 WHERE event_date IS NOT NULL AND event_time IS NOT NULL
), conflicts AS (
 SELECT url_key,event_date,count(DISTINCT event_time) AS clocks,
        array_agg(DISTINCT event_time ORDER BY event_time) AS times,
        array_agg(DISTINCT url ORDER BY url) AS urls
 FROM normalized GROUP BY url_key,event_date HAVING count(DISTINCT event_time)>1
)
SELECT url_key,event_date::text,clocks,times,urls FROM conflicts
ORDER BY event_date,url_key LIMIT 200"""


def summarize(rows):
    return {"status": "read_only", "conflict_groups": len(rows),
            "samples": [{"url": r[0], "date": r[1], "times": list(r[3]),
                         "urls": list(r[4]), "decision": "HOLD_URL_CLOCK_CONFLICT"}
                        for r in rows[:12]], "authorized_to_write": False,
            "note": "Trailing-slash variants only; query parameters remain significant. Different clocks may be separate sessions; human review required."}
