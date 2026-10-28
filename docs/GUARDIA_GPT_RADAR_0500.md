# Por Acá · Guardia GPT del Radar Definitivo · 05:00 ART

Fecha de instalación: 28/10/2026.

**Propósito:** vigilar el FULL habitual del Radar Definitivo de las 03:17 (Argentina). El captador de datos sigue siendo GitHub Actions, **nunca ChatGPT**. Esta Guardia sólo revisa ejecuciones y activa un mecanismo de recuperación si falta el FULL de la fecha.

**Tarea GPT activa:** `Por Acá — Guardia Radar 05:00` (todos los días 05:00 ART, zona America/Argentina/Buenos_Aires).

## Comprobación diaria

1. Consultar GitHub Actions en `diegomontenegroext-hash/poraca-explorador`, workflow `.github/workflows/radar-definitivo.yml`. Clasificar `event=schedule` vs `event=push` y resultados `queued/in_progress/completed + conclusion`.
2. Una corrida FULL programada exitosa o todavía ejecutándose **no** debe recibir una segunda ejecución. Una recuperación FULL ya iniciada también impide otra.
3. Si la FULL falta a las 05:00, o terminó `failure/cancelled` sin otra válida, leer `ops/radar-fallback-trigger.txt`; no actualizar si `fallback_date` ya contiene la fecha local.
4. Cuando haga falta, actualizar con el conector autenticado de GitHub `ops/radar-fallback-trigger.txt`, estableciendo `fallback_date=AAAA-MM-DD` y `fallback_reason=missing_or_failed_scheduled_full`. **Un commit a esta ruta dispara por push el mismo workflow, con modo FULL**, usando el secreto operativo `NEON_RADAR_OPERATIONAL_DATABASE_URL`.
5. Comprobar que aparezca la ejecución `event=push`; reportar su estado auténtico, URL y la eventual necesidad de seguimiento, sin declarar éxito sólo por crear el commit.
6. Si la herramienta no permite la actualización, informar claramente el fallo. No activar Work, no pedir credenciales, no volver a encender el viejo Radar ChatGPT.

## Controles

- Hay una sola ruta de contingencia `ops/radar-fallback-trigger.txt`, observada en `on.push.paths` del workflow principal. Es distinta del piloto manual.
- La tarea de GPT **no hace scraping**, no decide aceptación de eventos y no escribe directamente en Neon.
- El Radar definitivo registra candidatos únicamente en `neondb.radar_definitivo`, sin publicar eventos.
- La concurrencia de GitHub evita ejecuciones simultáneas de dos FULL, pero por sí sola no elimina la posibilidad de un segundo barrido diferido si el cron llega muy tarde. Hay deduplicación de URL y hay que comprobar recursos tras los primeros ciclos.
- El scheduler GitHub puede retrasar/omitir un cron; la tarea de GPT tiene su propio scheduler, por lo que no constituye garantía absoluta de puntualidad. Registrar siempre el resultado observado.

[Acciones del Radar Definitivo](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/workflows/radar-definitivo.yml)
