#!/usr/bin/env python3
"""Optional controlled browser read of Genda date pages; never web-wide crawling."""
from __future__ import annotations
from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit,parse_qs
import time

def validated_date_pages(urls, today=None):
    today=today or datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date()
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
                    # The rendered *visible text* keeps card lines that
                    # DOM template wrappers or hidden mobile duplicates can
                    # confuse when reparsed as generic HTML.
                    result[url]=page.locator("body").inner_text(timeout=5000)[:240_000]
                except Exception:
                    continue
            context.close()
            browser.close()
    except Exception as exc:
        return result, "BROWSER_RENDER_FAILED:"+type(exc).__name__
    return result,None


def render_argentino_event_pages(urls,max_seconds=55):
    """Read only explicit /meet/<id> Teatro Argentino event pages, no login."""
    from urllib.parse import urlsplit
    import re
    valid=[]
    for url in urls[:8]:
        parts=urlsplit(url)
        if (parts.scheme=="https" and parts.hostname=="teatroargentino.gba.gob.ar"
            and parts.port is None and not parts.query and not parts.fragment
            and re.fullmatch(r"/meet/[0-9]{1,8}/?",parts.path)
            and url not in valid):
            valid.append(url)
        if len(valid)>=4:break
    if not valid:return {},None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {},"BROWSER_PACKAGE_UNAVAILABLE"
    result={}
    start=time.monotonic()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="chrome",headless=True,
                                     args=["--no-sandbox","--disable-dev-shm-usage"])
            context=browser.new_context(locale="es-AR",timezone_id="America/Argentina/Buenos_Aires")
            context.set_default_timeout(6000)
            context.route("**/*",lambda route: route.abort()
                if route.request.resource_type in ("image","font","media") else route.continue_())
            page=context.new_page()
            for url in valid:
                if time.monotonic()-start>max_seconds-8:break
                try:
                    response=page.goto(url,wait_until="domcontentloaded",timeout=12000)
                    if response and response.status==429:break
                    if response and response.status>=400:continue
                    try:
                        page.wait_for_function(
                            "() => document.body?.innerText.includes('Fecha del evento')",
                            timeout=6500)
                    except Exception:pass
                    result[url]=page.content()[:650_000]
                except Exception:continue
            context.close()
            browser.close()
    except Exception as ex:
        return result,"BROWSER_RENDER_FAILED:"+type(ex).__name__
    return result,None


def validated_alpedo_date_pages(urls,today=None):
    """Only this known agenda's concrete dates, without arbitrary links."""
    today=today or datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
    result=[]
    for url in urls[:8]:
        try:p=urlsplit(url)
        except ValueError:continue
        if (p.scheme!="https" or p.hostname not in ("alpedo.ar","www.alpedo.ar")
            or p.path!="/" or p.port is not None or p.fragment or p.username or p.password):
            continue
        q=parse_qs(p.query)
        if set(q)!={"fecha"} or len(q["fecha"])!=1:continue
        try:d=date.fromisoformat(q["fecha"][0])
        except (ValueError,TypeError):continue
        if today<=d<=today+timedelta(days=4) and url not in result:
            result.append(url)
        if len(result)>=3:break
    return result


def render_alpedo_date_pages(urls,max_seconds=65):
    """Render at most 3 date URLs using the existing bounded browser pattern.

    Does not open Instagram, follow links or create entities; returns DOM
    text+tags only to the secondary-evidence parser.
    """
    valid=validated_alpedo_date_pages(urls)
    if not valid:return {},None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {},"BROWSER_PACKAGE_UNAVAILABLE"
    result={}
    start=time.monotonic()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="chrome",headless=True,
                args=["--no-sandbox","--disable-dev-shm-usage"])
            context=browser.new_context(locale="es-AR",
                timezone_id="America/Argentina/Buenos_Aires")
            context.set_default_timeout(5500)
            context.route("**/*",lambda route:
                route.abort() if route.request.resource_type in ("image","font","media")
                else route.continue_())
            page=context.new_page()
            for url in valid:
                if time.monotonic()-start>max_seconds-8:break
                try:
                    resp=page.goto(url,wait_until="domcontentloaded",timeout=11000)
                    if resp and resp.status==429:break
                    if resp and resp.status>=400:continue
                    try:
                        page.wait_for_function(
                            "() => document.querySelectorAll('h6').length >= 5",
                            timeout=6500)
                    except Exception:
                        pass
                    # Keep h6 and card siblings together in the HTML so the
                    # parser can associate ONE clock and ONE venue per card.
                    markup=page.content()[:450_000]
                    if "<h6" in markup.lower():
                        result[url]=markup
                except Exception:
                    continue
            context.close()
            browser.close()
    except Exception as exc:
        return result,"BROWSER_RENDER_FAILED:"+type(exc).__name__
    return result,None
