#!/usr/bin/env python3
"""Optional controlled browser read of Genda date pages; never web-wide crawling."""
from __future__ import annotations
from datetime import date,timedelta
from urllib.parse import urlsplit,parse_qs
import time

def validated_date_pages(urls, today=None):
    today=today or date.today()
    accepted=[]
    for url in urls[:5]:
        p=urlsplit(url)
        if p.scheme!="https" or p.hostname not in ("agendalaplata.ar","www.agendalaplata.ar") or p.path!="/" or p.port is not None:
            continue
        q=parse_qs(p.query)
        if set(q)!={"fecha"} or len(q["fecha"])!=1:continue
        try:d=date.fromisoformat(q["fecha"][0])
        except ValueError:continue
        if today<=d<=today+timedelta(days=5) and url not in accepted:
            accepted.append(url)
    return accepted

def render_date_pages(urls, max_seconds=75):
    """Read at most five date pages in one browser, with no login/interaction."""
    urls=validated_date_pages(urls)
    if not urls:
        return {},None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {},"BROWSER_PACKAGE_UNAVAILABLE"
    result={}
    started=time.monotonic()
    try:
        with sync_playwright() as p:
            # GitHub's ubuntu-latest runner includes stable Chrome. No browser
            # installation or external browser profile/credentials is required.
            browser=p.chromium.launch(channel="chrome",headless=True,
                                     args=["--no-sandbox","--disable-dev-shm-usage"])
            context=browser.new_context(locale="es-AR",timezone_id="America/Argentina/Buenos_Aires")
            context.set_default_timeout(6500)
            context.route("**/*",lambda route:
                route.abort() if route.request.resource_type in ("image","font","media")
                else route.continue_())
            page=context.new_page()
            for url in urls:
                if time.monotonic()-started>max_seconds-9:break
                try:
                    response=page.goto(url,wait_until="domcontentloaded",timeout=12000)
                    if response and response.status==429:
                        break
                    if response and response.status>=400:
                        continue
                    # Genda's client-side hydration may load cards after HTML.
                    try:
                        page.wait_for_function(
                            "() => /\\b\\d{1,2}:\\d{2}\\s*hs\\b/i.test(document.body.innerText)",
                            timeout=6500)
                    except Exception:
                        pass
                    result[url]=page.content()[:650_000]
                except Exception:
                    continue
            context.close()
            browser.close()
    except Exception as exc:
        return result, "BROWSER_RENDER_FAILED:"+type(exc).__name__
    return result,None
