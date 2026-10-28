# POR ACÁ — DOBLE EXPERIMENTO DE ESTABILIZACIÓN, 28/10/2026

## Decisión y alcance

**No limpiar Neon operativa.** La tabla `public.radar_agenda_events` tiene 159 eventos y alimenta la operación existente. El nuevo Radar ya tiene 157 candidatos y 25 ocurrencias estructuradas, pero muchos no constituyen eventos corroborados. Borrar los datos quitaría la referencia para medir cobertura y arriesgaría la web. Tampoco ejecutar otro FULL idéntico antes de adaptar la extracción: los barridos recientes consiguieron recorrer 63 fuentes pero 29 respuestas quedaron `index_only`.

**Dos iniciativas separadas:**
A. Recuperación rápida de los eventos conocidos mediante baseline persistida e ingeniería de adaptadores por fuente.
B. Diagnóstico de cron independiente de ChatGPT y del motor cultural, con latido real en Neon.

## A. Baseline congelada sin borrar datos

En Neon proyecto `frosty-union-52906378`, rama `br-mute-recipe-b4odj2bl` (`poraca-production`), DB `neondb`, esquema `radar_definitivo`:

- `canonical_baseline_snapshots`: `snapshot_id='baseline-20261028-v1'`; copia inmutable de **159** eventos, incluidos **51** con fecha desde 2026-10-28. Es una tabla auxiliar, no la de eventos publicada.
- `collection_snapshot_members`: congeló las claves de **157** candidatos y **25** ocurrencias. Las próximas se comparan contra esas claves sin reiniciar contadores, eliminar fuentes ni perder evidencia.
- `baseline_sync_status_v1`: vista dinámica que compara los 51 eventos originales con el corpus en crecimiento: `strong_candidate_match`, `original_url_seen_unverified`, `not_recovered_by_strict_match`. Punto de partida: **0 / 1 / 50**. Es un criterio estricto y conservador; cero coincidencias no implica que los eventos originales ya no existan.
- `fresh_collection_progress_v1`: cuenta candidaturas y ocurrencias realmente nuevas respecto de la fotografía; punto de partida 157/25 y **0/0 nuevas**.

Consultas:
```sql
SELECT snapshot_id,count(*),count(*) FILTER(WHERE event_date>='2026-10-28')
FROM radar_definitivo.canonical_baseline_snapshots GROUP BY snapshot_id;
SELECT * FROM radar_definitivo.fresh_collection_progress_v1;
SELECT sync_state,count(*) FROM radar_definitivo.baseline_sync_status_v1 GROUP BY sync_state;
SELECT event_key,title,event_date,venue,source_url,sync_state
FROM radar_definitivo.baseline_sync_status_v1
WHERE sync_state<>'strong_candidate_match'
ORDER BY event_date,title;
```

### Procedimiento del primer barrido manual útil

**No hacer otro FULL del mismo extractor sin cambios:** hoy ya se revisaron 63 webs, 27 `ok`, 29 `index_only`, 7 `failed`. El trabajo siguiente consiste en crear adaptadores específicos para **Alternativa Teatral /obra, Genda, Teatro Ópera, Casa Metro, Select/EcoSelect, ticketera Livepass, Lumenartis**, con pruebas contra URLs concretas de `baseline_sync_status_v1`, conservando múltiples funciones por obra y parámetros semánticos de fecha. Empezar por los 51 eventos futuros, emparejar por URL/canonical + título + fecha/hora/sala, registrar excepciones y no aceptar automáticamente.

Cuando pasen las pruebas, disparar **FULL de validación por `workflow_dispatch` o por el orquestador GPT según slot**; comparar `baseline_sync_status_v1` y `fresh_collection_progress_v1` antes/después. La métrica de éxito es fecha/horario/sede recuperados, no URLs nuevas sin validar.

## B. Prueba autónoma de cron GitHub (sin GPT)

**Workflow:** `.github/workflows/radar-cron-probe.yml` en `main`, independiente de `radar-definitivo.yml`. Tiene:
- `push` filtrado al propio YAML, para una **prueba control positiva**. El [run #40683631934](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40683631934) `event=push` resultó `SUCCESS`; guardó latido en Neon.
- `schedule` POSIX `13,43 12-17 28,29 10 *` en UTC: ventana 09:13, 09:43, ..., 14:43 **ART** los días 28 y 29/10/2026. Son 12 posibles disparos/día; al año siguiente la propia lógica evita escribir fuera de esos dos días. No se dispara desde la tarea GPT.
- Una tabla **aislada** `radar_definitivo.scheduler_probe_runs`: `github_run_id` como clave única, `event_type=push|schedule|workflow_dispatch`, cron, commit, hora de inserción y el texto `funcione`. No se borra nada y nunca se escribe en `public.radar_agenda_events`.
- Cliente psycopg, guard de `database=neondb`, login `poraca_definitivo_ingest`, `SET ROLE poraca_definitivo_scope` y control de no permiso de publicación. Secret existente, sin divulgarlo.
- Concurrencia propia y `timeout-minutes=4`; cada ejecución usa pocos segundos, no visita ninguna fuente cultural ni Instagram.

**Criterio de diagnóstico:** 
1. `event=push` correcto + registro Neon prueba conexión y workflow. Ya confirmado.
2. Primer `event=schedule` con latido demuestra que el scheduler GitHub puede activarse solo.
3. Si aparece `event=schedule` con `failure`, investigar logs y permisos (problema de ejecutor/Neon).
4. Si pasan varias ventanas y no aparece ningún `event=schedule`, investigar disparador GitHub: `main` default (ya confirmada), workflow no deshabilitado, actor de cron, programación POSIX UTC, backend de GitHub. GitHub documenta atrasos y posibles omisiones bajo carga; no confundir falta de cron con error de extracción. Evaluar soporte GitHub si el problema persiste.
5. El piloto es **temporal**, sus ventanas de octubre 2026 no deben convertirse en cadencia permanente. Cuando haya diagnóstico, archivarlo o limitarlo a revisión.

Consultas:
```sql
SELECT github_run_id,event_type,scheduled_cron,observed_at,status_text
FROM radar_definitivo.scheduler_probe_runs ORDER BY observed_at DESC;
SELECT event_type,count(*) FROM radar_definitivo.scheduler_probe_runs GROUP BY 1;
```

## Operación principal sin cambios

La tarea GPT **«Por Acá — Radar GitHub 3 veces al día»** permanece activa a 05:00 FULL / 13:00 y 21:00 incrementales ART. Es la programadora confiable que escribe en GitHub mediante el archivo `ops/radar-fallback-trigger.txt`. No invocar el viejo Radar GPT ni reconectar cron al Radar principal hasta comprobar el piloto de GitHub. Los modelos `sources,candidates,event_occurrences` se preservan; Motor/Puente/API/Vercel no cambiaron.

**Fuente de arquitectura:** [Plan de estabilización](PLAN_ESTABILIZACION_RADAR_20261028.md), backlog `poraca-lp#16` y `#28`.
