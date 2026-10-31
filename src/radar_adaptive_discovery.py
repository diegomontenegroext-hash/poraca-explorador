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
