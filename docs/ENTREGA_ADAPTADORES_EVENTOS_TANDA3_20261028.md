# Por Acá — Entrega de eventos · Tanda 3 (28/10/2026)

**Propósito:** aumentar recuperación REAL de funciones, sin entidades ni publicación automática. Trabajo implementado en `main` sobre `src/radar_agenda_adapters.py`, `src/radar_definitivo.py`, `src/radar_genda_browser.py` y tests.

## Evidencia previa y decisiones
- 51 eventos actuales/futuros congelados como baseline; antes de esta tanda había 12 coincidencias fuertes, 2 horarios en conflicto y 37 pendientes.
- Se inspeccionó HTML público efectivo de: Teatro Metro, Teatro Argentino, Lumen Artis, Agenda de Cine Select/EcoSelect. No se introdujeron fechas, URLs ni salas de forma hipotética.
- `choose_sources` utiliza las URL **originales ya registradas** como watchlist para Metro (`/entrada/`), Argentino (`/meet/`) y Lumen (`?p=...&post_type=funcion`), además de Alternativa y Casa Metro. Una URL de watchlist no crea evento por sí sola: se exige descarga o render de la fuente.
- No se ha ejecutado ninguna promoción de `radar_definitivo` a `public.radar_v3_source_observations` o `public.radar_agenda_events`. No hubo cambios en API/Vercel.

## Implementación probada en Neon
1. **Teatro Metro**: fichas de entradas y cartelera oficial, distinción fecha/hora del espectáculo de horarios de boletería; dos pruebas unitarias. [Run #40696205598](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40696205598) `SUCCESS` / Neon `complete`; tres fuentes revisadas, **cinco funciones Metro incorporadas**, 11 URLs nuevas en ese run. Sus dos URL de entrada con hora exacta y tres fichas de cartelera se preservan como evidencias independientes; posibles duplicados semánticos necesitan revisión.
2. **Lumen Artis**: fechas en español sin año explícito con ventana temporal restringida y título extraído del artículo (no desde baseline). En [run #40696954629](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40696954629) `SUCCESS` / Neon `complete`: dos fuentes revisadas, **3 funciones Lumen** incorporadas. No inventar programación recurrente ni fechas fuera de la ventana.
3. **Cine Select y EcoSelect**: parser dedicado a la cartelera mensual de `agendadecine.com`, fuente **secundaria especializada** con funciones individuales, título, fecha de octubre 2026, hora y sala concreta. Se añadió una fuente monitoreada de EcoSelect; Select ya existía. [Run #40697832519](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40697832519) `SUCCESS` / Neon `complete`: dos fuentes y **49 funciones estructuradas en staging**, de las cuales 15 tienen fecha desde el 28/10. No confundir 49 funciones de octubre con 49 eventos nuevos actuales. Se mantienen en `HOLD_SECONDARY_SOURCE` hasta corroborar originales de los cines municipales.
4. **Teatro Argentino**: fuente oficial `/meet/<id>` publica `Fecha del evento`, distinta de inicio/cierre de venta; parser y tests con HTML real simplificado instalados. Las páginas abren en GitHub, pero el primer extractor y la primera prueba Chrome regresaron **0 sesiones**, aunque tres páginas se renderizaron. Se añadió un diagnóstico no sensible (presencia del campo de fecha, tamaño del HTML) para identificar si el runner recibe contenido distinto del visto en navegador. **NO declarar el adaptador resuelto** hasta un run con `argentino_official_fecha_evento` y readback. Diagnóstico: [GitHub #40698684579](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40698684579), verificar resultado final.
5. Tests de fuente Metro, Argentino, Lumen, Select/EcoSelect, seguridad de URLs, múltiples funciones y protección de fechas de reserva: QA [#40698176427](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40698176427) `SUCCESS`, QA del diagnóstico [#40698553956](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40698553956) `SUCCESS`.

## Métricas acumuladas comprobadas
`radar_definitivo.listing_occurrences`:
- Genda: **32** (secundaria)
- Alternativa Teatral: **22**
- Casa Metro: **9**
- Ópera: **8** fechas sin horario
- Lumen Artis: **3**
- Metro: **5** (3 cartelera + 2 páginas de entradas)
- Agenda de Cine Select/EcoSelect: **49** (secundaria, 15 actuales/futuras)
- Total **128 registros de función**, incluyendo duplicados entre fuentes y sesiones pasadas; no son eventos canónicos únicos.

`baseline_event_parity_v2` sobre los **51 eventos** congelados: **17** coincidencias exactas fecha/hora/URL, **2** conflictos de horario, **32** sin recuperación con el criterio actual. No contar 49 de cine como matches fuertes del catálogo histórico si no tienen misma URL y corroboración primaria.

`observation_mapping_preview_v1` sigue **SELECT ONLY**, con numerosos HOLD secundarios, horarios no informados y fuentes aún no autorizadas. No cambiar estatus vía código de extracción. En particular, las referencias de cine deben buscar cartelera municipal/espacio original antes de aceptación.

## Siguiente ruta sin reingeniería
- **P0-A**: resolver Teatro Argentino /meet con diagnóstico de contenido real; ampliar cobertura de 32 eventos pendientes por origen, evitando carreras de FULL sin cambios.
- **P0-B**: reconciliar funciones duplicadas (ej. Metro ficha+cartelera, Genda+cines especializados) por nombre normalizado, fecha, horario y **sala**, con equivalencias conservadoras; conflictos en HOLD con originales y hora de consulta.
- **P0-C**: formalizar preview/dry-run de mapeo hacia `public.radar_v3_source_observations`, sin DML hasta prueba + autorización explícita, siguiendo reglas transaccionales existentes.
- **P0-D**: después, un evento admitido E2E hasta API / web privada SIN redeploy por información.
- **P0-E**: comprobar las tres tareas GPT 05 FULL / 13 y 21 incrementales. Cron probe GitHub aislado sólo diagnóstico, no sustituye el programador GPT sin evidencia real de `event=schedule`.

No reabrir Puente autónomo ni generar entidades, fotografías o fichas.
