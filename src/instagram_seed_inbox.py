"""Buzón acotado de enlaces exactos IG compartidos o descubiertos fuera del feed.

Nunca intenta recorrer perfiles, Stories ni búsquedas de Instagram.
La cola usa cuentas ya inventariadas como discover_only y conserva la
diferencia entre una publicación revisada y un perfil monitorizado.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

MAX_SEED_ACCOUNTS = 3
MAX_SEEDS_PER_ACCOUNT = 2
REVISIT_HOURS = 36
INBOX = Path(__file__).resolve().parents[1] / "ops" / "instagram-exact-seeds.json"
PERMALINK = re.compile(r"^/(p|reel)/([A-Za-z0-9_-]{5,50})/?$")
ACCOUNT = re.compile(r"^[a-zA-Z0-9_.]{2,30}$")


def normalized_post(url):
    """Sólo URL exacta y pública: sin redirecciones, query ni hosts arbitrarios."""
    try:
        p = urlsplit(url)
        m = PERMALINK.fullmatch(p.path)
        if (p.scheme != "https" or p.hostname not in
            {"instagram.com", "www.instagram.com"} or p.port not in (None, 443)
            or p.username or p.password or p.query or p.fragment or not m):
            return None
        return f"https://www.instagram.com/{m[1]}/{m[2]}/"
    except (ValueError, TypeError):
        return None


def read_inbox(path=INBOX, today=None):
    today = today or datetime.now(timezone.utc).date()
    try:
        entries = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    if not isinstance(entries, list):
        raise ValueError("Instagram inbox must be an array")
    if len(entries) > 100:
        raise ValueError("Instagram inbox unbounded")
    unique = set()
    active = []
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("Invalid Instagram inbox entry")
        url = normalized_post(item.get("url"))
        source_id = item.get("source_id", "")
        account = item.get("account", "")
        until = item.get("expires_on", "")
        if not (url and isinstance(source_id, str) and
                re.fullmatch(r"rd-ig-[a-z0-9_-]+", source_id) and
                isinstance(account, str) and ACCOUNT.fullmatch(account) and
                source_id == "rd-ig-" + account.lower() and
                isinstance(until, str)):
            raise ValueError("Invalid exact IG seed or account")
        expires = date.fromisoformat(until)
        if expires < today:
            continue
        if (source_id, url) not in unique:
            unique.add((source_id, url))
            active.append((source_id, account.lower(), url))
    return active


def choose_seed_sources(conn, path=INBOX, today=None):
    """Selecciona solamente URLs aún no vistas recientemente, atribuidas a inventario.

    Los perfiles no se solicitan y su last_checked_at no cambia.
    """
    active = read_inbox(path, today=today)
    if not active:
        return []
    ids = sorted({x[0] for x in active})
    urls = sorted({x[2] for x in active})
    with conn.cursor() as cur:
        cur.execute("""SELECT source_id,name,url,source_role,priority,cadence_hours,
                             consecutive_failures
                         FROM radar_definitivo.sources
                         WHERE source_id=ANY(%s) AND enabled
                           AND monitoring_mode='discover_only'""", (ids,))
        inventory = {row[0]: row for row in cur.fetchall()}
        cur.execute("""SELECT url FROM radar_definitivo.candidates
                       WHERE url=ANY(%s)
                         AND last_seen_at>=now()-(%s*interval '1 hour')""",
                    (urls, REVISIT_HOURS))
        seen = {row[0] for row in cur.fetchall()}
    grouped = {}
    for source_id, account, url in active:
        row = inventory.get(source_id)
        if not row or url in seen:
            continue
        # Fuente catalogada y cuenta indicada deben coincidir.
        p = urlsplit(row[2])
        if (p.hostname not in {"instagram.com", "www.instagram.com"} or
            p.path.strip("/").lower() != account):
            continue
        group = grouped.setdefault(source_id, dict(
            source_id=row[0], name=row[1], url=row[2], source_role=row[3],
            priority=row[4], cadence_hours=row[5], consecutive_failures=row[6],
            seed_urls=[], seed_only=True, account=account))
        if len(group["seed_urls"]) < MAX_SEEDS_PER_ACCOUNT:
            group["seed_urls"].append(url)
    return list(grouped.values())[:MAX_SEED_ACCOUNTS]
