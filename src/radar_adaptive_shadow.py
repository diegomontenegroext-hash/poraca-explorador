#!/usr/bin/env python3
"""Propuesta reversible de política por fuente: SIMULACIÓN, nunca orquestación.

No I/O, SQL, red, escrituras, acciones, admisión editorial ni cron.
Las señales provienen del readback SQL de la misma ventana histórica.
Un modo propuesto NO es prueba de utilidad o de modalidad definitiva.
"""
from __future__ import annotations


MODES = {
    "discover_only": "exploracion_indirecta_no_feed",
    "review": "explorar_si_hay_evidencia",
}


def _nonnegative(facts, key):
    return max(0, int(facts.get(key) or 0))


def assess(facts):
    """Clasificar sin usar nombres de dominio ni cambiar el scheduler.

    Ventana de 7 días: los datos observados no equivalen a aprobaciones.
    Nunca penaliza automáticamente entidades con actividades permanentes.
    """
    monitoring = str(facts.get("monitoring_mode") or "")
    checks = _nonnegative(facts, "checks_7d")
    index_only = _nonnegative(facts, "index_only_7d")
    failed = _nonnegative(facts, "failed_7d")
    new = _nonnegative(facts, "new_7d")
    primary = _nonnegative(facts, "primary_new_7d")
    future = _nonnegative(facts, "future_sessions")
    if monitoring in MODES:
        mode = MODES[monitoring]
        reason = "endpoint no habilitado para fetch: conservar su modalidad"
    elif primary >= 2:
        mode = "priorizar_original"
        reason = "funciones nuevas con evidencia primaria; revisar aporte marginal"
    elif new >= 3:
        mode = "reconciliar_agenda_secundaria"
        reason = "varias detecciones; falta evaluar confirmación y duplicación"
    elif checks >= 2 and index_only == checks:
        mode = "diagnosticar_canal_o_valor_institucional"
        reason = "visitas sin sesiones extraídas; puede ser referencia cultural"
    elif checks >= 2 and new == 0:
        mode = "verificar_utilidad_antes_de_reducir"
        reason = "sin sesiones nuevas; confirmar necesidad de conservar la frecuencia"
    else:
        mode = "exploracion_controlada"
        reason = "mantener cuota de exploración; historial todavía poco concluyente"
    score = (min(primary, 10)*5 + min(new, 20)*2
             + min(future, 10) - min(index_only, 5)*2 - min(failed, 5)*3)
    return {
        "mode_shadow": mode,
        "score_shadow": score,
        "confidence": "insuficiente" if checks < 3 else "preliminar",
        "reason": reason,
        "action_state": "DRY_RUN_ONLY",
        "changes_to_sources": False,
        "changes_to_editorial": False,
        "auto_publish": False,
    }
