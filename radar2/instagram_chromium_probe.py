#!/usr/bin/env python3
"""One-shot, bounded Chromium diagnostic for Instagram public profile visibility.

No authentication, proxies, stealth settings, CAPTCHA handling, scrolling,
pagination or Neon writes. A 200 response does NOT prove posts were retrieved.
This is NOT a production collector; it tests whether standard Chromium on
GitHub Actions can see any post references on three public account pages.
"""
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout

USERS = ("guajira.bar", "ciudaddegatos", "casametrolp")
POST = re.compile(r"/(?:p|reel)/([A-Za-z0-9_-]{5,})")
MAX_HTML = 1500000

def one(browser, username):
    url = "https://www.instagram.com/" + username + "/"
    result = {"username": username, "requested": url, "utc": datetime.now(timezone.utc).isoformat(),
              "http_status": None, "final_host": None, "post_links": 0,
              "post_urls_sample": [], "caption_bearing_cards": 0,
              "html_post_markers": 0, "login_or_challenge": False, "error": None}
    page = browser.new_page()
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=22000)
        result["http_status"] = response.status if response else None
        page.wait_for_timeout(2500)  # initial rendering only, no scrolling
        result["final_host"] = urlsplit(page.url).hostname
        html = page.content()[:MAX_HTML]
        result["html_post_markers"] = len(re.findall(r'["\\\']shortcode["\\\']\\s*:', html))
        cards = page.locator('a[href*="/p/"], a[href*="/reel/"]')
        links = []
        captions = 0
        for card in cards.all()[:60]:
            href = card.get_attribute("href") or ""
            match = POST.search(href)
            if match:
                kind = "reel" if "/reel/" in href else "p"
                links.append("https://www.instagram.com/" + kind + "/" + match.group(1) + "/")
                if card.locator("img[alt]").count():
                    alt = card.locator("img[alt]").first.get_attribute("alt") or ""
                    if len(alt.strip()) > 35:
                        captions += 1
        unique = list(dict.fromkeys(links))
        result["post_links"] = len(unique)
        result["post_urls_sample"] = unique[:2]
        result["caption_bearing_cards"] = captions
        result["login_or_challenge"] = ("/accounts/login" in page.url or "/challenge" in page.url
            or "login_and_signup_page" in html or "Login • Instagram" in (page.title() or ""))
        result["classification"] = ("POST_LINKS_VISIBLE" if unique
               else "ACCESS_RESTRICTED" if result["http_status"] in (401, 403, 429) or result["login_or_challenge"]
               else "HTML_MARKERS_ONLY" if result["html_post_markers"]
               else "NO_POSTS_VISIBLE")
    except (BrowserTimeout, Exception) as error:
        result["classification"] = "BROWSER_ERROR"
        result["error"] = type(error).__name__ + ": " + str(error)[:200]
    finally:
        page.close()
    return result

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        try:
            results = [one(browser, u) for u in USERS]
        finally:
            browser.close()
    print("INSTAGRAM_CHROMIUM_PUBLIC_PROBE " + json.dumps(results, ensure_ascii=False))
    summary = "\n".join("| " + str(x["username"]) + " | " + str(x["http_status"]) +
                 " | " + str(x["post_links"]) + " | " + str(x["caption_bearing_cards"]) +
                 " | " + str(x["classification"]) + " |" for x in results)
    import os
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf8") as f:
            f.write("## Instagram — Chromium público (diagnóstico único, no ingesta)\n\n")
            f.write("| Perfil | HTTP | Enlaces de posts | Cards con texto | Resultado |\n|---|---:|---:|---:|---|\n" + summary + "\n\n")
            f.write("Sin login, stealth, proxies, bypass, scroll, Neon ni reintentos. HTTP 200 no implica lectura de posts.\n")

if __name__ == "__main__":
    main()
