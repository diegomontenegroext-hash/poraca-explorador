# Por Acá — puente de fuentes autorizadas (read-only)
**Corte:** 03/11/2026. **Dueño:** #10 (Editorial) y #28 (Radar).
**Estado al cierre:** puente validado; 2 observaciones internas de El Ánimo escritas en producción y retenidas; **NO** publicaciones.

## Problema que corrige
Radar utiliza `radar_definitivo.sources.source_id`, mientras que el escritor editorial
`poraca_apply_cultural_batch_v1` verifica fuentes en `public.radar_web_sources_v1`.
Una coincidencia de origen por nombre de dominio NO autoriza la inserción automática;
se requiere exactamente una fuente de rol permitido y una entidad sede pública ya admitida.
La identidad de fuente del extractor se preserva en el informe para auditoría, pero el
`editorial_source_id` es el único origen candidato para una futura observación editorial.

## Validación realizada
Consulta directa `SELECT` de [sql/20261103_editorial_handoff_gap_READ_ONLY.sql](../sql/20261103_editorial_handoff_gap_READ_ONLY.sql)
contra Neon `frosty-union-52906378`, producción `br-mute-recipe-b4odj2bl`: **92** propuestas,
**2** `MANUAL_REVIEW_FOR_OBSERVATION_ONLY`:
- El Ánimo, viernes **06/11/2026 21:00**, sede `en-eso-estamos`, fuente editorial `src-alternativa-teatral`; proposed ID `obs-stage-f416b398b13ad999fc693019`.
- El Ánimo, viernes **27/11/2026 21:00**, misma sede y fuente; proposed ID `obs-stage-780e4b6e4e4c424c457034f7`.

Original [Alternativa Teatral](https://www.alternativateatral.com/obra103415-el-animo)
especifica ambos viernes a las 21:00; también contiene funciones históricas.
El mapeo exige dominio único y rol autorizado, no interpreta entradas complementarias,
horas de apertura de puertas ni ciclos como funciones nuevas.

**Resto de la cohorte (90):** 19 índices sin detalle, 19 fuentes editoriales
no conciliadas, 16 variantes de sede, 12 sedes sin identidad aprobada, 11
posibles canónicos, 10 observaciones existentes, 1 HOLD previo, 1 conflicto
horario y 1 entrada accesoria. Son prioridades de revisión, no 90 errores de Radar.

**QA Neon `br-icy-night-b4larkc3`:** 0 casos listos. Las dos observaciones
de El Ánimo ya existen en QA con `conflict=pending_editorial_handoff_review` y
`publication=DO_NOT_APPROVE`, por lo que el nuevo puente las retiene.
Esa rama es una fotografía antigua; los totales de ella NO se comparan con producción
para medir rendimiento.

**Límite de autoridad:** `poraca_definitivo_scope` no tiene SELECT sobre
`public.radar_web_sources_v1` ni `public.poraca_knowledge_entities`.
Este preflight es lectura de dueño editorial, no se ejecuta automáticamente
desde Radar ni justifica GRANTs, INSERT/UPDATE o cambio de roles.

## Próxima fase
Revisión editorial individual de los dos originales, generar observaciones
con procedencia, idempotencia y `publicationApproved=false` por vía autorizada;
readback de ambas filas con IDs, dos fechas, cero canónicos creados; ejecutar
escritor de evento solo con autorización editorial posterior y prueba API/web.
No correr FULL extra, no crear cron ni nueva rama; mantener IICS **5,2/10**
hasta acreditar un gate real.


## Readback posterior · 03/11/2026

El lote de El Ánimo generó **2** observaciones en producción, ninguna canónica, bajo `DO_NOT_APPROVE`. QA seguía con 2 HOLD de un ensayo anterior, sin duplicados. [Código del lote](../sql/20261103_editorial_observation_safe_batch_v1.sql) y [QA final PASS](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41698412185).

**Freezer 2026 — una fuente, no 19 parches:** el programa original [festival.freezer.com.ar/2026/programacion](https://festival.freezer.com.ar/2026/programacion/) fue contrastado con la extracción Radar `rd-official-freezer-2026`. Se dio de alta en `public.radar_web_sources_v1` de QA y producción como `src-freezer-festival-2026-original`, `institutional_program`, `arte_y_cultura`, `enabled` y política explícita: distinguir horario de apertura/actividad, fecha, sala y cupo; prohibido aprobar automáticamente. **19 propuestas** dejaron de estar `HOLD_AUTHORIZED_SOURCE_MAPPING` y pasaron a `HOLD_APPROVED_VENUE_MAPPING`. Existe 1 evento Freezer previo posiblemente canónico; **no** se publicó uno nuevo por esta alta.

Las 19 propuestas retenidas tienen **10 etiquetas de sede**. Se identificaron entidades públicas existentes relevantes: `centro-arte` (Centro de Arte UNLP), `casa-62` (Casa 62) y `pasaje-dardo-rocha` (Centro Cultural Pasaje Dardo Rocha). **No** adjudicar automáticamente los subespacios *Espacio Dickinson*, *Sala A* o *Auditorio* por compartir edificio/dirección. Conciliar con evidencia de pertenencia y conservar el nombre de sala en la ficha. Teatro Metro continúa `verified_internal` y no equivale a Casa Metro; sin promoción ficticia.

**Estado IICS inalterado: 5,2/10.** Sin QA de Actions para este ajuste de documentación: se conservó el QA del código sobre su SHA antes de escribir.
