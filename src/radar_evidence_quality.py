"""Read-only evidence-quality counters from Radar's existing staging listings.

Not a resolver or admission mechanism. Repeated secondary agendas never
count as independent originals. Does not mutate rows or infer venues.
"""
from collections import defaultdict
import re
import unicodedata

AGENDA_G="rd-web-47c7b7b9"
AGENDA_A="rd-web-cb094233"
SECONDARY={AGENDA_G,AGENDA_A}

def norm(text):
    plain=unicodedata.normalize("NFKD",str(text or ""))
    plain="".join(c for c in plain if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+","",plain.casefold())

def contaminated(venue):
    return bool(venue and re.search(
        r"<|>|class\s*=|document\.|javascript:",venue,re.I))

def specific_original(url):
    """Allow only event/work/detail links from explicitly known ticket domains."""
    from urllib.parse import urlsplit
    try:
        u=urlsplit(str(url or ""))
        host=(u.hostname or "").lower().removeprefix("www.")
        path=u.path
        if u.scheme!="https" or not host or u.username or u.password:
            return False
        rules={
            "alternativateatral.com":r"/obra\d+(?:-[a-z0-9-]+)?/?",
            "teatrometrolp.com.ar":r"/entrada/[a-z0-9-]+/?",
            "casametro.com.ar":r"/evento/[a-z0-9-]+/?",
            "teatroargentino.gba.gob.ar":r"/meet/\d+/?",
            "livepass.com.ar":r"/events/[a-z0-9-]+/?"
        }
        return host in rules and bool(re.fullmatch(rules[host],path,re.I))
    except ValueError:
        return False

def summarize(rows):
    """Sequence rows: source_id,title,ISO-date,time,venue,proof_url,evidence_tier."""
    groups=defaultdict(list)
    contaminated_rows=0
    missing_venue=0
    count=0
    for source,title,day,clock,venue,proof,tier in rows:
        count+=1
        if contaminated(venue):
            contaminated_rows+=1
            continue
        if not venue:
            missing_venue+=1
            continue
        if not (title and day and clock and proof):
            continue
        key=(norm(title),str(day),str(clock),norm(venue))
        if not all(key):
            continue
        groups[key].append((source,proof,tier))
    mirrored=0
    matched_primary=0
    for observations in groups.values():
        sources={src for src,_,_ in observations}
        if SECONDARY.issubset(sources):
            mirrored+=1
        if sources & SECONDARY and any(
            tier and str(tier).startswith("primary") and src not in SECONDARY
            and specific_original(proof)
            for src,proof,tier in observations):
            matched_primary+=1
    return {
        "status":"read_only",
        "listing_rows":count,
        "malformed_venue_rows":contaminated_rows,
        "missing_venue_rows":missing_venue,
        "shared_genda_alpedo_functions":mirrored,
        "secondary_keys_with_specific_primary_detail":matched_primary,
        "auto_accepted":0,
        "note":"Source overlap is not independent evidence; only recognized primary detail URLs are counted for further review."
    }
