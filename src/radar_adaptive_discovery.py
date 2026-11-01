#!/usr/bin/env python3
"""Descubrimiento reutilizable, de alcance limitado, de secciones de agenda.

NO conoce dominios ni inventa URLs. Se activa sólo si la extracción conocida
no encontró enlaces; es un fallback de navegación, no un evento confirmado.
No hace red, JS, escritura o promoción editorial.
"""
from __future__ import annotations
from urllib.parse import urljoin, urlsplit
import unicodedata
import re

TOPICS = (
    ("calendario", "agenda", "programacion", "cartelera", "eventos", "event"),
    ("actividades", "actividad", "novedades", "actualidad", "shows", "espectaculos",
     "ferias", "festival", "degustaciones", "exposiciones", "muestras"),
    ("musica", "cine", "teatro", "artes", "talleres", "clases", "cursos", "cultura"),
)
EXCLUDE = {"contacto","nosotros","acerca","institucional","home","inicio",
           "login","registrarse","donaciones","suscripcion","privacidad","terms",
           "legal","carrito","checkout","productos","tienda","buscar","search"}


def normalized(s):
    value=unicodedata.normalize("NFKD",s or "")
    value="".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+"," ",value.lower()).strip()


def discover_sections(base_url, links, limit=3):
    """Links **reales** del HTML del mismo host, a un único nivel.

    La prioridad está en menú de calendario, luego programas/actividades.
    Nunca seguir más de 3 enlaces adicionales y solo cuando no se dispone
    de otros detalles. Páginas categoría = navegación, no evento.
    """
    base=urlsplit(base_url)
    if base.scheme!="https" or not base.hostname:
        return []
    found={}
    for href,label in links[:900]:
        href=(href or "").strip()
        if not href or href.startswith(("//","javascript:","mailto:","tel:")):
            continue
        try:
            p=urlsplit(urljoin(base_url,href))
            if (p.scheme!="https" or p.hostname != base.hostname
                or p.username or p.password or p.port not in (None,443)
                or p.query or p.fragment or not p.path):
                continue
        except ValueError:
            continue
        path=p.path.rstrip("/")
        parts=[x for x in path.split("/") if x]
        if len(parts)!=1 or len(parts[0])>70:
            continue
        tokens=set(normalized(parts[0]+" "+(label or "")).split())
        if tokens & EXCLUDE:
            continue
        quality=next((3-i for i,group in enumerate(TOPICS)
                      if tokens.intersection(group)),0)
        if quality==0:
            continue
        url="https://"+p.hostname+path+"/"
        existing=found.get(url)
        if existing is None or quality>existing:
            found[url]=quality
    return [(url,"adaptive_section_link") for url,score in
            sorted(found.items(),key=lambda row:(-row[1],row[0]))[:max(0,min(limit,3))]]


# Signals describe an event article, not a specific publisher's URL structure.
ORIGINAL_POST_HINTS={"concierto","obra","funcion","funciones","recital",
                     "estreno","presentacion","charla","conferencia",
                     "espectaculo","festival","seminario","proyeccion",
                     "exposicion","muestra","taller","ciclo","encuentro"}
GENERIC_SECTION_NAMES={"musica","artes","visuales","escenicas","audiovisuales",
                       "cine","teatro","eventos","agenda","programacion",
                       "calendario","actividades","novedades","cursos",
                       "exposiciones","muestras","talleres","info",
                       "informacion","categoria","archivo","blog","noticias"}


def discover_original_posts_from_section(section_url, links, existing=(), limit=1):
    """One bounded same-host article hop from an already fetched section.

    Generic to *any* first-party institutional site: it never searches the
    web, invents slugs, follows external links or treats a link as an event.
    The real article must still independently provide an explicit clock/date
    to the appropriate parser. Preserve budget-neutral selection.
    """
    base=urlsplit(section_url)
    if (base.scheme!="https" or not base.hostname or base.username or
            base.password or base.port not in (None,443)):
        return []
    prior=set()
    for value in existing:
        prior_url=value[0] if isinstance(value,tuple) else value
        p=urlsplit(prior_url)
        if p.hostname==base.hostname:
            prior.add(p.path.rstrip("/").lower())
    found={}
    for href,label in links[:250]:
        raw=(href or "").strip()
        if not raw or raw.startswith(("//","javascript:","mailto:","tel:","#")):
            continue
        try:
            p=urlsplit(urljoin(section_url,raw))
            if (p.scheme!="https" or p.hostname!=base.hostname or
                    p.username or p.password or p.port not in (None,443) or
                    p.query or p.fragment or not p.path):
                continue
        except ValueError:
            continue
        path=p.path.rstrip("/")
        parts=[part for part in path.split("/") if part]
        if (not 1<=len(parts)<=3 or len(path)>230 or
                path.lower() in prior or path.lower()==base.path.rstrip("/").lower()
                or re.search(r"\.(?:png|jpg|jpeg|webp|svg|pdf|mp4|ics|xml)$",path,re.I)):
            continue
        tokens=set(normalized(" ".join(parts)+" "+(label or "")).split())
        if tokens & EXCLUDE:
            continue
        last_tokens=normalized(parts[-1]).split()
        if (not last_tokens or len(last_tokens)>16 or
                (len(last_tokens)<=2 and all(t in GENERIC_SECTION_NAMES for t in last_tokens))):
            continue
        signal=bool(tokens & ORIGINAL_POST_HINTS)
        # Event-sounding originals come first. Other descriptive post slugs
        # can still be visited: the parser, not navigation, decides if event.
        descriptive=len(last_tokens)>=3 and len(normalized(label or ""))>=8
        if not (signal or descriptive):
            continue
        score=2*int(signal)+int(descriptive)
        candidate="https://"+p.hostname+p.path
        if candidate not in found or found[candidate]<score:
            found[candidate]=score
    return [(url,"original enlazado desde sección institucional")
            for url,score in sorted(found.items(),key=lambda x:(-x[1],x[0]))[:max(0,min(limit,3))]]
