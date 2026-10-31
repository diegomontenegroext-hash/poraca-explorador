"""Certificación punta a punta, de solo lectura y sin falsos aprobados.

Separar "caso bajo prueba" (fixture), "contrato" (unit) y "real" (Neon,
HTTP protegido, cuentas accesibles). El resultado macro NUNCA es CERTIFIED
si falta evidencia de cualquier puerta crítica. No hace I/O ni publicaciones.
"""
from __future__ import annotations

SCHEMA="poraca-certification-e2e-v1"

CASES=(
 ("C01","scheduler","Disparo único sin corrida concurrente","unit+live"),
 ("C02","source","Fuente nueva desconocida con HTML de agenda","fixture"),
 ("C03","source","Enlace de agenda cambia de nombre o ruta","fixture"),
 ("C04","source","La fuente líder desaparece y surge una alternativa","controlled+live"),
 ("C05","source","HTTP 403, 429, captcha o bloqueo de cuenta","controlled+live"),
 ("C06","source","Respuesta 200 sin funciones y pérdida de rendimiento","live"),
 ("C07","source","Fuente nunca antes vista sin reputación","controlled+live"),
 ("C08","source","Distinción original, medio y agregadora espejo","fixture+live"),
 ("C09","source","Cuota exploratoria para disciplinas minoritarias","controlled+live"),
 ("C10","format","JSON-LD Event de dominio nuevo sin ascenso a primaria","fixture"),
 ("C11","format","HTML con tarjetas y múltiples funciones","fixture+live"),
 ("C12","format","RSS o Atom descubierto desde vínculo real","controlled+live"),
 ("C13","format","ICS de organizador nuevo, no solo feed conocido","controlled+live"),
 ("C14","format","Calendario renderizado en JavaScript","controlled+live"),
 ("C15","format","Cartelera cambia de HTML a ICS o viceversa","controlled+live"),
 ("C16","format","Afiche OCR o imagen accesible","controlled+live"),
 ("C17","format","Reel con audio, subtítulos y descripción","controlled+live"),
 ("C18","format","Red social cambia a carrusel o texto","controlled+live"),
 ("C19","format","Publicación no accesible o contenido retirado","controlled+live"),
 ("C20","semantic","Actividad recurrente sin fechas explícitas","fixture+live"),
 ("C21","semantic","Deporte o grupo recreativo nuevo, fuera de teatro","live"),
 ("C22","semantic","Espacio nuevo, organizador y localización distintos","controlled+live"),
 ("C23","semantic","Actualización de centro cultural existente","controlled+live"),
 ("C24","semantic","Varias funciones de la misma obra","fixture+live"),
 ("C25","semantic","Evento reprogramado: nueva fecha y prueba original","controlled+live"),
 ("C26","semantic","Evento cancelado: evitar agenda vigente engañosa","controlled+live"),
 ("C27","semantic","Cambio de sede sin duplicar evento","fixture+live"),
 ("C28","semantic","Distintas fuentes reportan misma función","fixture+live"),
 ("C29","semantic","Horarios diferentes NO se fusionan","fixture+live"),
 ("C30","semantic","Recomendaciones laterales de ticket ajeno","fixture+live"),
 ("C31","semantic","Sede desconocida o inscripción por privado","fixture"),
 ("C32","semantic","Fuente secundaria sin original queda pendiente","fixture+live"),
 ("C33","neon","Persistencia con clave idempotente y procedencia","fixture+live"),
 ("C34","neon","Historial y archivo se conservan tras reset","live"),
 ("C35","neon","Aprendizaje por fuente separado de éxito HTTP","live"),
 ("C36","neon","Deriva de formato medida con huella versionada","controlled+live"),
 ("C37","editorial","Staging se convierte en observación editorial","live"),
 ("C38","editorial","Conflicto en un caso no bloquea el resto","controlled+live"),
 ("C39","editorial","La aprobación no es automática por tener JSON-LD","fixture+live"),
 ("C40","editorial","Canónico futuro autorizado, con lugar y circuito","live"),
 ("C41","api","API protegida devuelve evento aprobado","protected_http"),
 ("C42","web","SSO y agenda navegable en móvil y escritorio","protected_browser"),
 ("C43","web","Primera visita encuentra eventos hoy y mañana","protected_browser"),
 ("C44","web","Búsqueda under, vinos, yoga, cerámica y deportes","protected_browser"),
 ("C45","operations","Rollback de selector sin perder evidencia","controlled"),
 ("C46","operations","No nuevas tareas, cron duplicado o publicación espuria","live"),
)

CRITICAL=("acquisition","staging","editorial_handoff","future_canonicals",
          "api_http","web_ssos","crosslink_quality","source_recovery")
STATES=("PASS","FAIL","BLOCKED","NOT_TESTED")


def classify(facts):
    """Factos versionados, obtenidos por SELECT; nunca inventar HTTP/SSO."""
    def n(k):return max(0,int(facts.get(k) or 0))
    def gate(key,state,why):
        return {"gate":key,"state":state,"reason":why}
    done=n("checked_sources")
    selected=n("selected_sources")
    complete=(selected>0 and done==selected
              and facts.get("run_finished") is True)
    issues=n("suspect_crosslinks")
    g=[
       gate("acquisition","PASS" if complete else "FAIL",
            "Todas las fuentes seleccionadas se chequearon"
             if complete else "Corrida incompleta o no terminada"),
       gate("staging","PASS" if n("future_staging")>0 else "FAIL",
            "Existe evidencia futura en staging" if n("future_staging") else
            "No hay evidencias de eventos futuros"),
       gate("primary_evidence","PASS" if n("future_primary_complete")>0 else "FAIL",
            "Algunas sesiones tienen prueba primaria, hora y sede" if
            n("future_primary_complete") else "No hay funciones primarias completas"),
       gate("editorial_handoff","PASS" if n("editorial_touched_since_run")>0 else "FAIL",
            "Se actualizaron observaciones editoriales" if n("editorial_touched_since_run")
            else "No hay nueva actividad editorial desde esta corrida"),
       gate("future_canonicals","PASS" if n("future_canonical")>0 else "FAIL",
            "Catálogo contiene futuros" if n("future_canonical") else
            "Catálogo no contiene eventos futuros"),
       gate("crosslink_quality","PASS" if issues==0 else "FAIL",
            "No se detectan tickets ajenos" if issues==0 else
            "Persisten asociaciones sospechosas sin certificar"),
       gate("source_recovery","NOT_TESTED","No hay prueba live de sustitución tras caída"),
       gate("source_drift","NOT_TESTED","No hay huella/versiones probadas de cambio de formato"),
       gate("generic_ics","NOT_TESTED","Parser y descubrimiento genéricos con QA; falta feed real nuevo"),
       gate("multimodal_social","NOT_TESTED","No hay prueba de video, imagen y caption accesibles"),
       gate("sports_discovery","PASS" if n("active_sports_sources")>0 else "FAIL",
            "Existen canales deportivos activos" if n("active_sports_sources")>0
            else "No hay canal deportivo activo demostrado por el inventario"),
       gate("api_http",facts.get("api_http_status","NOT_TESTED"),
            "Solo un chequeo HTTP autenticado del origen exacto da PASS"),
       gate("web_ssos",facts.get("web_ssos_status","NOT_TESTED"),
            "READY de Vercel no equivale a prueba de navegación autenticada"),
    ]
    for x in g: 
        if x["state"] not in STATES:raise ValueError("Estado no certificado: "+str(x))
    by={x["gate"]:x["state"] for x in g}
    ok=all(by[key]=="PASS" for key in CRITICAL)
    return {"schema":SCHEMA,"state":"CERTIFIED" if ok else "NOT_CERTIFIED",
            "gates":g,"counts":{s:sum(x["state"]==s for x in g) for s in STATES},
            "cases_defined":len(CASES),
            "cases_executed":n("cases_executed"),
            "warning":"No confundir tests de fixtures con pruebas live ni evidencia con admisión."}
