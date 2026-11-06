#!/usr/bin/env python3
"""Single-run, diagnostic replication of the 04/11 HTTP public-profile experiment.

One ordinary GET per username, no retries, cookies, authentication, JS,
proxy, browser, hidden API endpoint, bypass, persistent captures or Neon writes.
Only summary counts are logged; this is not a production collector.
"""
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UA = "PorAc/2.0 (+https://github.com/diegomontenegroext-hash/poraca-explorador; cultural research)"
USERS = ("guajira.bar", "lutitravelguide")
MAX_BYTES = 6_000_000

class EmbeddedScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.parts = []
        self.current = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            self.inside = dict(attrs).get("type", "").lower() == "application/json"
            self.current = []
    def handle_data(self, value):
        if self.inside:
            self.current.append(value)
    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.inside:
            self.parts.append("".join(self.current))
            self.current = []
            self.inside = False

def scan(node, found):
    if isinstance(node, dict):
        code = node.get("shortcode") or node.get("code")
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_-]{6,20}", code):
            caption = node.get("caption")
            if isinstance(caption, dict):
                caption = caption.get("text", "")
            if caption is None:
                caption = ""
            found.setdefault(code, bool(str(caption).strip()))
            if str(caption).strip():
                found[code] = True
        for v in node.values():
            scan(v, found)
    elif isinstance(node, list):
        for v in node:
            scan(v, found)

def probe(username):
    url = "https://www.instagram.com/" + username + "/"
    result = dict(profile=username, method="single_public_http_get_no_login", utc=datetime.now(timezone.utc).isoformat(),
                  status=None, bytes_received=0, json_scripts=0, shortcodes_json=0, captions_json=0,
                  shortcodes_raw=0, login_marker=False, category="unclassified", error=None)
    try:
        with urlopen(Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}), timeout=18) as resp:
            result["status"] = resp.status
            body = resp.read(MAX_BYTES + 1)
            result["bytes_received"] = len(body)
            truncated = len(body) > MAX_BYTES
            html = body[:MAX_BYTES].decode("utf-8", "replace")
        result["truncated"] = truncated
        parser = EmbeddedScripts()
        parser.feed(html)
        result["json_scripts"] = len(parser.parts)
        found = {}
        for data in parser.parts:
            try:
                scan(json.loads(data), found)
            except (json.JSONDecodeError, RecursionError):
                pass
        result["shortcodes_json"] = len(found)
        result["captions_json"] = sum(found.values())
        result["shortcodes_raw"] = len(set(re.findall(r'"shortcode"\s*:\s*"([A-Za-z0-9_-]{6,20})"', html)))
        result["login_marker"] = bool(re.search(r'login_and_signup_page|/accounts/login|Login • Instagram|Login to Instagram', html, re.I))
        result["category"] = ("POSTS_IN_EMBEDDED_JSON" if found else
          "POST_CODE_MARKERS_ONLY" if result["shortcodes_raw"] else
          "LOGIN_OR_RESTRICTION" if result["login_marker"] else "NO_POST_DATA_FOUND")
    except HTTPError as e:
        result.update(status=e.code, category="HTTP_ERROR", error="HTTPError")
    except (URLError, TimeoutError, OSError) as e:
        result.update(category="NETWORK_ERROR", error=type(e).__name__)
    return result

def main():
    results = [probe(username) for username in USERS]
    print("INSTAGRAM_ORIGINAL_HTTP_DIAGNOSTIC " + json.dumps(results, ensure_ascii=False))
    import os
    if path := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(path, "a", encoding="utf-8") as f:
            f.write("## Repetición acotada de HTTP directo, sin navegador\n\n")
            f.write("| Perfil | HTTP | Bytes | JSON scripts | Posts JSON | Captions JSON | Clasificación |\n|---|---:|---:|---:|---:|---:|---|\n")
            for r in results:
                f.write("| "+r["profile"]+" | "+str(r["status"])+" | "+str(r["bytes_received"])+" | "+str(r["json_scripts"])+" | "+str(r["shortcodes_json"])+" | "+str(r["captions_json"])+" | "+r["category"]+" |\n")
            f.write("\nUna petición por perfil, sin reintentos ni almacenamiento de contenido. Un HTTP 200 no equivale a recuperar publicaciones.\n")

if __name__ == "__main__":
    main()
