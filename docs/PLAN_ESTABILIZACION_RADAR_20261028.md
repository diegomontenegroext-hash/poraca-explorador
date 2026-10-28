# POR ACÁ — ESTABILIZACIÓN DEL RADAR DEFINITIVO 1.0
**Decisión:** 28 de octubre de 2026. **Ejecución real:** GitHub Actions. **Programador de contingencia temporal:** una sola tarea ChatGPT. **Persistencia:** Neon rama `poraca-production`, DB `neondb`, schema `radar_definitivo`. **Fuente de verdad pública:** tablas existentes de Motor, sin escrituras automáticas a `public.radar_agenda_events`.

## 0. Diagnóstico comprobado

1. GitHub no registró ninguna ejecución `event=schedule` en las primeras pruebas. Sí registró ejecuciones `event=push`, incluidas las disparadas desde la Guardia de ChatGPT.
2. Guardia 05:00 ART del 28/10: ejecutó con éxito un commit a `ops/radar-fallback-trigger.txt`, disparó [GitHub #40654017927](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40654017927) y quedó lectura real en `neondb`. FULL: 63/63 fuentes visitadas, 27 `ok`, 29 `index_only` (HTML 200 sin actividades extraídas), siete `failed`, 118 URLs candidatas vistas, cero nuevas.
3. `neondb` operativo mantiene **159 eventos** en `public.radar_agenda_events`; **51** son eventos fechados desde el 28/10 en adelante. La vista QA `radar_definitivo.agenda_baseline_coverage_v1` halla **0 emparejamientos estrictos por título+fecha**, **1 URL de fuente recuperada sin ocurrencia cotejada**, **50 sin enlace recuperado**. **Advertencia:** esto es un cotejo estricto inicial, no una afirmación de que 50 eventos hayan desaparecido ni una medida definitiva de cobertura semántica. Hacen falta resolución de alias, enlaces y recurrencias.
4. Inventario Radar: 225 fuentes catalogadas, 63 URL web bajo `fetch` (mezcla de agendas verdaderas, sitios institucionales, páginas históricas puntuales), 39 en revisión y 123 perfiles Instagram `discover_only` que aún no se recorren como feeds.
5. Al inicio de esta etapa: 157 URLs candidatas, ~25 ocurrencias estructuradas, todas sin publicación automática. **Problema:** la ingesta no produce aún una cantidad equivalente de eventos estructurados respecto de la agenda operativa.
6. El actual generador es genérico: busca enlaces seleccionados y JSON-LD Event. Muchas agendas usan enlaces no convencionales, múltiples funciones por obra, filtros/JS, paginación, nombres de funciones o fechas en prosa. Un `200` no equivale a extracción. No resolver esto simplemente elevando límites o reintentando HTTP.

## 1. Programador estable: implementado y probado

Se reemplazó la Guardia de una vez/día por la **única tarea activa de GPT «Por Acá — Radar GitHub 3 veces al día»**, horarios ART:
- **05:00** → `full`
- **13:00** → `incremental`
- **21:00** → `incremental`

GitHub `.github/workflows/radar-definitivo.yml` **no tiene `schedule`**, por ahora; escucha exclusivamente `push` del archivo `ops/radar-fallback-trigger.txt` o `workflow_dispatch` manual. Ese archivo lleva `trigger_date=AAAA-MM-DD`, `trigger_slot=05/13/21`, `trigger_mode=full/incremental` y motivo. Cada tarea GPT: comprueba ejecución previa, impide duplicación de slot, actualiza sólo este archivo y lee status en GitHub/Neon. No es recolector, no navega Instagram y no llama Work/Codex. GitHub hace el trabajo pesado y escribe en `neondb.radar_definitivo`. Si no puede crear el commit, registra fallo, no inventa ejecución.

**Prueba de integración:** `ops/radar-fallback-trigger.txt` actualizado con `slot=bootstrap`, `mode=incremental` produjo [GitHub #40682506769](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40682506769), `event=push`, `SUCCESS`, y registro Neon `mode=incremental`, `status=complete`, `target=operational_neondb_staging`. La prueba seleccionó 0 fuentes vencidas (correcto a esa hora; **no demuestra adquisición incremental**).

Para que las corridas del mediodía/noche no sean siempre vacías, se ajustaron las **13 fuentes prioritarias accesibles** (`priority>=75`, excluyendo error de red) a `cadence_hours=7`; se reprogramó `next_due_at` a siete horas después de la última visita, sin borrarlas. Fuentes fallidas conservan backoff. Las demás mantienen cadencia propia y entran al FULL diario.

**Pendiente:** comprobar al menos una ejecución programada GPT 13:00 y 21:00 reales con fuentes vencidas; 05:00 siguiente FULL; observar si el cron de GitHub realmente se omite (fuera de producción, diagnóstico separado).

## 2. Etapa A — paridad de agendas operativas (prioridad absoluta)

Objetivo primario: contrastar **los 51 eventos vigentes o futuros** de la agenda operativa con hallazgos del nuevo Radar, sin sobrescribir ni publicar datos. Para cada evento generar estados `encontrado_coincidencia_fuerte`, `encontrado_ambigua`, `fuente_abierta_sin_evento`, `original_inaccesible`, `no_buscado`. Todas las diferencias deben tener fuente, URL original, último intento y próxima acción.

Primera tanda — adaptadores de las grandes agendas, no un extractor universal:
1. **Alternativa Teatral**: listado por localidad, páginas de obra `/obra...`, funciones por fecha y hora (varias ocurrencias por obra), entradas de teatro/conciertos.
2. **Genda / Agenda La Plata**: inspeccionar HTML/JS/RSS/JSON/endpoint público real, agenda y fichas; si necesita JS, estudiar adaptador de render, no inventar URLs.
3. **Teatro Ópera, Teatro Metro, Teatro Argentino, Casa Metro**: carteleras oficiales, distintas salas y fechas, páginas de tickets/categorías.
4. **0221, El Día, Alpedó, Casa Dionisio, Luti, La Plata Tango**: páginas de listado y notas con enlaces a originales, varios eventos por nota y enlaces de publicación exacta.
5. **Select/EcoSelect, UNLP y museos**: funciones diarias, recurrencias, múltiples sesiones, y calendario institucional.
Las fuentes que hoy son `index_only` deben tener un diagnóstico individual: `EMPTY`, `JS_RENDERED`, `PAGINATED`, `FILTER_NOT_MATCHED`, `LINK_BLOCKED`, `PAST_ONLY`, no solo HTTP 200.

**Criterio de cierre de la Etapa A:** los 51 eventos de referencia deben estar **cada uno recuperado con fecha/hora/sede o registrado como excepción verificable con causa y próxima fuente**, y la vista de cobertura debe mostrar sus cifras separadas por estado. No declarar 100% si una ficha está sólo en un artículo sin fecha validada. Objetivo de ingeniería: >=90% emparejamientos fuertes y 100% de divergencias explicadas; el umbral puede corregirse según accesibilidad genuina.

## 3. Etapa B — normalización, deduplicación y memoria

Schema destino `radar_definitivo`, sin nueva arquitectura central. Modelo conceptual:
- `sources`: fuente identificable, modalidad, prioridad, frecuencia, ultimo resultado y próxima revisión; reapertura por novedad.
- `candidates`: página/post con URL y evidencia, título/descripción, procedencia, fecha de descubrimiento/última vista, imagen referencial.
- `event_occurrences`: **una función por fecha/hora/sede**, vinculada a una obra/evento, permitiendo ciclos y cambios.
- `candidate_sources`: varias fuentes corroborando un mismo evento.
- `entities`: propuesta de artista, colectivo, lugar, sala y organizador con prueba; no promoción automática.
- `link_edges`: relaciones entre agenda, noticia, publicación original y ticketera.

Reglas: URL canónica (conservar parámetros semánticos de fecha); dedupe técnico por URL y semántico propuesto por nombre normalizado + fecha + hora + sede; **jamás fusionar automáticamente** ante conflicto de sala o fecha; conservar cancelaciones y cambios con evidencia. Prioridad a fuente organizadora/primaria; medios y terceros complementan. ISO de fechas en ART, hora local y texto de fecha original preservado. `RUN_SUCCESS` técnico separado de `coverage_success` editorial.

## 4. Etapa C — QA de fuentes y continuidad

- Dos incremental y un FULL por día durante 3–7 días, **sin incrementar aún** 360 solicitudes/24min/24 Instagram exactos por corrida. 4 s de separación entre publicaciones; suspender host que devuelve 429.
- Estado por fuente en cada corrida: `ok`, `index_only`, `failed`, `rate_limited`, `not_due`, `skipped_by_budget`; registrar tiempos y siguiente intento.
- Alarmas: GPT no pudo disparar; GitHub no creó run; job `failure`; Neon sin run o sin acuses nuevos; >24 h sin revisión de una fuente prioritaria; duplicación inesperada; cero candidatos *con fechas* en un conjunto de agendas corroboradas.
- Métricas comparables por run: fuentes intentadas, index_only, HTTP 429, detalles abiertos, ocurrencias válidas, candidatos nuevos, duplicados, fuentes pendientes, duración, solicitudes, bytes aproximados en Neon.
- Un resumen diario con baseline de 51 eventos: recuperados fuertes, solo enlace, ambiguos, no recuperados, inaccesibles. Mantener como meta calidad y cobertura, no cantidad de candidatos.
- Error en fuente no debe abortar todo; commit por fuente y acuse persistente. Un disparo duplicado no crea doble evento canónico ni hace publicaciones.

## 5. Etapa D — ampliar descubrimiento tras paridad

Rehabilitar exhaustivamente inventario de **123 perfiles culturales de Instagram** sólo mediante fuentes públicas y enlaces a posts/reels exactos accesibles; no asumir 123 feeds legibles. Agregar espacios/clases/talleres/cerámica/teatro, fuentes nuevas observadas desde artículos, ciclos/artistas/entidades con imágenes y procedencia. Nuevas fuentes entran `review`, pasan a `fetch` tras demostración de actividad, y se degradan tras inactividad prolongada. La expansión no debe competir con el cierre de las agendas prioritarias.

## 6. Integración Motor/Puente/Web: gate separado

No sustituir la API ni volcar candidatos sin revisar. La vista `radar_definitivo.motor_observations_preview` permite evaluar compatibilidad, pero el nuevo Radar aún no escribe en las tablas públicas de observaciones/agenda del Motor. Sólo cuando la Etapa A/B tenga pruebas, desarrollar promoción de **observaciones pendientes**, reconciliación Motor y aceptación con fuentes, seguida de validación E2E del Puente y web privada. Mantener histórico de todo evento y ficha.

## Backlog y decisiones

Issue maestro `poraca-lp#16`, Radar `#28`; repositorio ejecutor `diegomontenegroext-hash/poraca-explorador`. Esta etapa prioriza **cobertura cultural real** sobre nuevos ejecutores, cambios de UI, fuentes de Instagram masivas o incremento de infraestructura. Si GitHub demuestra cron autónomo bajo test independiente, considerar volver a un scheduler único; la Guardia GPT funciona ahora y puede seguir como vigilancia.
