# Por Acá · Cierre técnico del caso testigo y dos identidades prioritarias
Fecha de control: 02/11/2026 (ART). **Sin autorización de publicación ni DML sobre catálogo.**

## A. Malena Muyala — 21/11/2026 22:00

**Primera parte:** https://casametro.com.ar/evento/malena-muyala/ (Casa Metro, Sala A; 21/11 22:00). El mismo organizador publica su programación https://casametro.com.ar/categoria-producto/casa-metro/ y enlaza la función. Esto es evidencia propia del recinto, no reseña ni inferencia de un título.

**Neon PROD (consulta 02/11):** tres observaciones `radar_definitivo.listing_occurrences` con coincidencia *literal* de título/día/hora/sala/URL oficial, en tres source IDs (NO son tres corroboraciones independientes: la página de origen es UNA). Existen cinco observaciones más amplias que coinciden en título/día/hora; dos expresan `Casa Metro` sin sala o una agenda derivada. **No fusionar toda la información en cinco eventos**. `public.poraca_knowledge_entities.entity_id='casa-metro'`: venue, `approved_public`, sin merged ID. `public.radar_agenda_events`: 0 colisiones por URL de origen o título+hora+recinto; sin canon de Malena. `public.radar_v3_checkpoints.stage='cultural_pipeline_v1'`: **0 recibos de decisión ACCEPTED_EVENT** vinculados a esa URL.

**Readback ejecutado:**
- [SQL del paquete](../sql/20261102_editorial_candidate_chain_READ_ONLY.sql): `READY_FOR_INDEPENDENT_EDITORIAL_DECISION_NOT_RELEASED`, 3 observaciones primarias coincidentes, 5 pistas brutas similares, 1 entidad host aprobada, 0 colisiones canónicas, **0 recibos editoriales**.
- [Pruebas positivas y negativas](../sql/20261102_editorial_candidate_negative_gates_READ_ONLY.sql): **5/5 PASS** sobre Neon PROD, incluidas hora alternativa, sala distinta, URL distinta y host no aprobado. Todas marcan `publication_approved=false`.
- [CI #41440846323](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41440846323) **SUCCESS**, prueba estática de que SQL no tiene comandos de escritura y exige campos de identidad.

**Puerta pendiente para un evento nuevo EN LA WEB:** decisión editorial independiente registrada con identidad estable, sujeto/auditor y recibo fechados; verificar específicamente sala, fuente original, hora del SHOW y unicidad; luego admisión por el mecanismo autorizado y lectura canónica + `/api/agenda` + web SSO. No ejecutar un `INSERT` directo para aparentar un E2E exitoso ni modificar `observed_unverified` sin recibo. La UI ya elimina el duplicado visual `RADAR_DIRECT` vs `EDITORIAL_LEGACY`.

## B. Entidades prioritarias con identidad aprobada pero sin minicard vigente

Ambas existen en `poraca_knowledge_entities` como `approved_public`, pero no tienen afirmación **aceptada** de `descripcion`, `direccion`, `ubicacion`, `primary_topic`, `principal_actividad` o `identidad_del_canal` con `evidence_tier IN(first_party,official,institutional)`. La mini API requiere por lo menos una. La ausencia actual NO prueba cierre físico.

### Pasaje Dardo Rocha (`pasaje-dardo-rocha`)

- Entidad con `official_url=https://turismo.laplata.gob.ar/circuitos-impredibles.html`; única afirmación aceptada actual: `review_schedule` de tipo `unknown` (no vale como hecho identitario).
- **Fuente institucional de identidad y lugar:** Banco Audiovisual FILMA de Provincia: https://bafilma.gba.gob.ar/locaciones/la-plata/centro-cultural-pasaje-dardo-rocha — define centro cultural, dirección Calle 50 entre 6 y Av. 7, antecedentes del edificio.
- **Corroboración de dirección:** Instituto Cultural Provincia: https://institutocultural.gba.gob.ar/taxonomy/term/1640 — Sala Cine Municipal Select en Pasaje Dardo Rocha, calle 50 n.º 575 entre 6 y 7, La Plata.
- **Actualidad diferenciada:** noticia de actividad municipal 30/07/2026 https://www.diarioplatense.com.ar/nota.php?Id=21522. No usarla como reemplazo de una prueba de programación vigente al 02/11.
- Proponer para revisión: afirmación `direccion` e identidad `centro cultural municipal`, evidencia institucional. **No insertar automáticamente ni aprobar agenda.**

### En Eso Estamos (`en-eso-estamos`)

- Entidad con Instagram oficial `https://www.instagram.com/en_eso_estamos/`; dos afirmaciones aceptadas `radar_source_id`, `review_schedule`, ambas `unknown` y sin hecho de ficha.
- **Primera parte organizadora:** https://enesoestamosfc.wordpress.com/ — «Fábrica Cultural», autogestión; dirección informada en el propio espacio: **calle 62 n.º 274 entre 1 y 115, La Plata**.
- **Institucional académico:** https://www.memoria.fahce.unlp.edu.ar/extension/px.378/px.378.pdf — proyecto de Extensión UNLP documenta la entidad, dirección 62 n.º 274, biblioteca y actividades; es fuente histórica, no confirmación automática de funcionamiento actual.
- **Cuidado de identidad temporal:** catálogos históricos pueden listar **calle 8 n.º 460** como dirección previa y «cerrado». El propio relato histórico del colectivo dice que surgió allí en 2010 y señala una sede posterior en calle 62; no inferir de un agregado obsoleto que la institución actual cerró.
- Proponer para revisión: afirmación `descripcion` de identidad/fábrica autogestiva y dirección oficial actual declarada por el propio colectivo; antes de atestar actividad verificada a noviembre, requerir evidencia actual, no solo el blog de años anteriores.
- **No cambiar la cuenta Instagram oficial ni duplicar entidad.**

## C. Próximo criterio de cierre

- P1 expediente Malena: recepción de decisión editorial por el flujo autorizado, inserción idempotente solo después de la decisión y chequeo API/Web; negativa a duplicados y funciones con otro reloj.
- P1 fichas: revisión/aceptación de una afirmación primaria REAL por cada entidad, sin bajar requisitos de calidad. Después comprobar 51→53 mini **si y solo si** los recibos resultan aceptados. No afirmar que esa cifra ya cambió.
- P1 index_only: observar próxima FULL natural luego de mejoras CI `4ba3947`, `175f4d0` y no cambiar 32 modos sin corroboración.
- P2 3/7 días y SSO Chromium real: evidencia temporal y navegador protegido, no simular PASS.

**La seguridad del proceso requiere que el diagnóstico y la revisión no se confundan con la aceptación de una publicación.** El bloqueo de redacción está resuelto; el recibo faltante sigue siendo una puerta editorial.
