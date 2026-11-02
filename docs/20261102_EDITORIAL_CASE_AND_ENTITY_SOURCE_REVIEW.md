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

## D. Verificación oficial adicional — mismo evento, cinco observaciones

Relectura **02/11/2026**, sin DML sobre Neon, rama `br-mute-recipe-b4odj2bl`, base `neondb`:

- `radar_definitivo.listing_occurrences`: **5 registros** con título Malena Muyala, fecha 21/11 y hora 22:00; son **una función potencial, no cinco**, con 4 IDs de fuente distintos. Tres registros recuperan el **mismo enlace primario** `https://casametro.com.ar/evento/malena-muyala/`, uno usa la tarjeta oficial general `https://casametro.com.ar/categoria-producto/casa-metro/` y otro una agenda secundaria `https://agendalaplata.ar/?fecha=2026-11-21`. No tratar múltiples monitores de una URL como corroboraciones independientes.
- El [original del recinto](https://casametro.com.ar/evento/malena-muyala/) confirma **sábado 21/11/2026, 22:00, Sala A de Casa Metro, calle 4 entre 51 y 53, La Plata**, y conserva enlace a entradas. La [programación oficial](https://casametro.com.ar/categoria-producto/casa-metro/) presenta el espectáculo en la fecha exacta. [Teatrina](https://teatrina.com/obras/malena-muyala) coincide en identidad, día, hora y sala; [Agenda La Plata](https://agendalaplata.ar/evento/malena-muyala-casa-metro-20261024025141) indica la dirección 4 n.º 978 entre 51 y 53. Confirmación cruzada **del hecho**, no de independencia de sistemas editoriales.
- `public.radar_agenda_events` devuelve **0 coincidencias** título+día; `review_state` de los cinco registros sigue `observed_unverified`. No se certificó recepción de una decisión de un editor identificado ni su readback API/web.
- **Se diferencia de otras fechas históricas** con Malena Muyala (por ejemplo el concierto «Las Mismas» del 20/06/2026 junto a Ana Prada). No fusionar por artista ni título sin fecha/función.
- **Recomendación editorial preparada, NO ejecutada:** aceptar **un** expediente de función con `title=Malena Muyala`, `event_date=2026-11-21`, `event_time=22:00`, `venue=Sala A - Casa Metro`, `category=musica`, `source_url` igual al enlace original. Antes de escribir: revisión independiente del registro, sujeto/fecha de decisión, recibo `ACCEPTED_EVENT`, identidad de venue aprobada y prueba negativa sobre horario/sala distintos; luego admisión idempotente por flujo existente y readback Neon→API→web. **Ninguna aprobación ni publicación fue realizada**.

Esta investigación consolida la evidencia; no debe convertir `EDITORIAL_ADMISSION` en verde por el solo hecho de que la ficha pública exista.
