# Por Acá — Entrega técnica: adaptadores de eventos, primera tanda (28/10/2026)

**Objetivo:** recuperar funciones reales con fecha/hora/sede desde originales sin modificar eventos públicos ni abrir el frente de entidades.

## Implementado en main

- `src/radar_agenda_adapters.py`: funciones por obra desde **Alternativa Teatral** (múltiples horarios y días), campos explícitos de **Casa Metro** en español, grilla oficial de fechas del **Ópera**, navegación diaria `?fecha=YYYY-MM-DD` de **Genda**, y soporte adicional para listas/grafos **JSON-LD con varias funciones** (conversión horaria a Argentina). Solo acepta ventanas temporales de hasta 14 días anteriores y 365 posteriores como *candidatos*. No infiere horas ausentes ni declara confirmaciones.
- `src/radar_definitivo.py`: admite estos adaptadores, conserva parámetros reales de fecha y `p/post_type`, abre enlaces externos de **Livepass** publicados en la página oficial del Ópera (no enlaces arbitrarios), y usa una lista de **URLs ORIGINALES ya conocidas** de la fotografía Neon para intentar recuperar obras de Alternativa/Casa Metro. Se registra la fuente de watchlist, **pero únicamente un acceso real al original puede originar un nuevo dato**. La watchlist rota primero hacia las URLs menos visitadas. No usar la baseline para fabricar funciones.
- `radar_definitivo.listing_occurrences` en Neon `neondb`: una fila por función, con fecha, hora, sede, fuente, método, nivel de evidencia, primer/último run y contador. Dedupe por hash estable y `ON CONFLICT` no duplicante.
- **Entidades fuera de alcance:** la propuesta automática de nuevas entidades desde JSON-LD fue desactivada por defecto (`RADAR_ENABLE_ENTITY_PROPOSALS=false`). No se borraron entidades históricas.
- `tests/test_radar_agenda_adapters.py` y QA GitHub verifican las páginas con ejemplos concretos, varios horarios, fechas españolas, Genda por fecha, URLs completas, caducidad y grafos JSON-LD.

## Primera FULL comparativa: ejecución REAL

[GitHub Action #40686529153](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40686529153), `event=push`, **SUCCESS del job GitHub**, ingestión `partial` (fuentes no cubiertas).

`run_id=definitivo-20261028T121710Z-133a8b`

- 63/63 fuentes visitadas, **31 ok**, 26 `index_only`, seis fallidas.
- 204 solicitudes HTTP, diez Instagram, 270 links identificados, 141 candidatos encontrados, **23 URLs candidatas nuevas**.
- **15 funciones en `listing_occurrences`: nueve Casa Metro y seis Alternativa**; todas `observed_unverified`, aunque algunas ya existían en las observaciones anteriores.
- Frente a los **51 eventos de la fotografía**, la vista de paridad `radar_definitivo.baseline_event_parity_v2` ahora muestra **5** coincidencias exactas de URL original, fecha y hora; **46** todavía no recuperados con este detector. Anteriormente el detector estricto arrojaba 0. Los cinco ejemplos: Casa Metro (Sofía Calvo 01/11, Sandra Mihanovich 06/11, Julieta Laso 14/11), Alternativa Teatral (Volcada y Cuadriláteros 6, 30/10).
- **Genda:** el Radar ahora abre cinco páginas por fecha (mejoría comprobada de navegación), pero aún genera **0 sesiones** con HTTP sin navegador; el caso sigue abierto como problema de HTML/JS y requiere diagnóstico de extracción real. **Ópera:** abre hasta seis enlaces reales de Livepass de los ocho publicados, pero sus títulos/fechas oficiales no generan todavía filas en `listing_occurrences` desde el índice. Varias páginas de Livepass sí aportan JSON-LD en `event_occurrences`.

**Incidencias de consistencia, en HOLD, sin actualizar canónicos:**
- Carmen Sánchez Viamonte 07/11: dato histórico **21:00**, JSON-LD de la ticketera **20:00**.
- Benjamín Amadeo 21/11: dato histórico **20:30**, JSON-LD de la ticketera **20:00**.
La vista `radar_definitivo.baseline_time_conflicts_v1` deja explícitos los dos conflictos. Requieren abrir y corroborar fuente original de horarios y, de ser necesario, conservar cambios de programación con fecha de evidencia.

## Preparación del resto de la cadena, sin publicar

- Vista `radar_definitivo.baseline_event_parity_v2`: referencia congelada vs funciones nuevas, solo lectura.
- Vista `radar_definitivo.baseline_time_conflicts_v1`: fechas iguales pero horarios contradictorios, HOLD.
- Vista `radar_definitivo.observation_mapping_preview_v1`: clasifica filas de `listing_occurrences` y `event_occurrences` por `ALREADY_IN_PUBLIC_OBSERVATIONS`, `READY_FOR_MANUAL_ORIGINAL_REVIEW`, `HOLD_MISSING_TIME`, `HOLD_MISSING_VENUE`, `HOLD_SECONDARY_SOURCE`, `HOLD_SOURCE_NOT_AUTHORIZED` o `HOLD_TIME_CONFLICT`. **Es SELECT únicamente**: no escribe en `public.radar_v3_source_observations` ni en `public.radar_agenda_events`.
- Primer corte de esta vista: **10** ya presentes en observaciones públicas, **9** listos solo para revisión manual del original (NO aceptación), 16 con host no autorizado, seis sin sede, dos secundarios y dos en conflicto de horario. El contrato de fuentes de `public.radar_web_sources_v1` sigue independiente; no autorizar automáticamente Livepass por estar enlazado desde Ópera.

## Próxima tanda antes de nueva FULL

1. Diagnosticar por qué Genda devuelve contenido visible pero no extraíble con HTTP sin JS; y las fechas de la cartelera del Ópera frente a las URLs de tickets. No elevar el volumen de scraping para taparlo.
2. Rotar la watchlist de Alternativa para los próximos originales sin funcion observada, cubrir múltiples horarios por obra y añadir fuentes oficiales Select/EcoSelect con un adaptador basado en evidencia.
3. Hacer **dry-run** de un pequeño lote de funciones en `observation_mapping_preview_v1` y revisar los nueve casos potencialmente elegibles; no promover a pública ni aceptar sin autorización y QA.
4. Seguir cron de la tarea GPT 05 FULL / 13 y 21 incremental. Mantener el piloto cron independiente.
5. Resolver las dos discrepancias Livepass en HOLD sin reescribir los horarios aceptados hasta verificar.

**No se modificó el código de la web, ni se publicó Vercel.** No se borró ningún evento ni se reactivó Puente/Motor como ejecutores.
