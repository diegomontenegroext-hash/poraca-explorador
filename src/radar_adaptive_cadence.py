#!/usr/bin/env python3
"""Cadencia incremental basada en evidencia reciente, reversible y acotada.

La FULL sigue recorriendo fuentes activas. No cambia estado de una entidad,
prioridad de origen, modo de monitoreo ni publica eventos. El historial es
consultado inmediatamente después de insertar el chequeo actual.
"""
from __future__ import annotations


def cadence_hours(base_hours, statuses, status, failures=0):
    base=max(1,min(168,int(base_hours or 24)))
    if status=="failed":
        return min(48,2**min(5,max(1,int(failures))))
    if status!="index_only":
        return base
    streak=0
    for item in statuses[:7]:
        if item!="index_only":
            break
        streak+=1
    # Primero recupera rápido un fallo de extracción. Si persiste, deja
    # de insistir en cada incremental y vuelve en la FULL diaria.
    if streak>=4:
        return max(base,72)
    if streak>=2:
        return max(base,24)
    return min(base,12)
