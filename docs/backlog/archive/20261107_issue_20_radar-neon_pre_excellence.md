# Archivo íntegro previo a la depuración del backlog · 07/11/2026 ART

**Issue:** https://github.com/diegomontenegroext-hash/poraca-explorador/issues/20
**Propósito:** conservar antecedentes y decisiones anteriores sin presentarlos como tareas aún abiertas. La fuente operativa es el issue vigente.

---

## CIERRE PUNTA A PUNTA — 07/11/2026 · Radar y Neon ACTUALIZADOS

**Ejecución real verificada en Neon:** 17 propuestas `caption-v2.3→v2.4` versionadas bajo guardas exactas (mismo ID/título/fecha/hora/original): **6 sedes literales recuperadas** y **11 sedes sugeridas** en `evidence.venue_candidate` con procedencia y cuenta tipada, **0 sugerencias promovidas**, `review_state` editorial conservado. La nueva FULL natural `radar2-ghdaily-42384154135-attempt1` terminó completed y **preservó las 17**; 988 documentos originales, 1.793 propuestas al corte posterior. Materializaciones de 33 categorías El Día + 62 Genda se conservan; ninguna aprobación automática.

**Revisión de conciliación:** 80 alias de propuestas enlazados en Neon sin eliminaciones y agrupaciones exactas adicionales; 1 cruce de fechas corresponde a **programa multifecha 7–8/11 (Exposición Ciudad Abierta)** y una función del día 8, ya marcado `contradictorio`: no alterar sin resolver semántica de programa/función. La observación física continúa en su registro, con evidencia. Los conteos de la vista `private_discoveries` cambian tras conciliación y no deben interpretarse como pérdida de originales.

**Qué queda realmente en #20:** conocimiento progresivo de cuentas que aún figuran sin rol seguro, evaluación independiente de falsos matches, composiciones y medianoches, y observación natural de las tres ventanas. La API y UX son #30, y la admisión editorial #16; **no repetirlos aquí**. [Contrato y ruta de cierre](https://github.com/diegomontenegroext-hash/poraca-lp/blob/main/docs/qa/20261107_RUTA_UNICA_CIERRE_RADAR_PORACA.md). **No reiniciar Neon ni ampliar permisos de `poraca_radar_limited_prod`.**

---

## IMPLEMENTADO: perfil cultural antes de cada consulta Meta — 07/11/2026

**Código en `main`, sin ejecución SQL de escritura ni cambios en Vercel/web/protección.** El perfil de cuenta ahora se conoce **antes de pedir publicaciones a Meta**, no después de extraer el texto.

- `radar2/account_profiles.json`: **43 perfiles con fuentes**; 40 cuentas enlazadas a sedes `approved_public` en el catálogo de Neon o con referencia pública corroborada; una sede interna todavía no pública (`teatroespacio44`), una cuenta curadora (`lutitravelguide`) y un artista itinerante (`sindicatoargentinodeboleros`). Snapshot de solo lectura porque el rol `poraca_radar_limited_prod` tiene **SELECT=false** sobre `public.poraca_knowledge_entities`. No ampliar ese permiso sin revisión.
- `radar2/account_context.py`: preflight `handle → tipo de cuenta → entidad/sede autorizada → evidencia → nombre/alias`. Si la cuenta no está identificada, devuelve `unclassified`; nunca la trata automáticamente como sala.
- `radar2/instagram_official_pilot.py`: genera el diagnóstico `account_preflight` **antes** de cualquier llamada al API oficial y añade procedencia por cuenta a la ejecución (sin búsquedas adicionales ni nuevas credenciales).
- `radar2/caption.py`: **`caption-v2.4`** incorpora sede únicamente cuando el **fragmento de ese evento** contiene alias comprobable de sala o dirección física en contexto de sala propia. En caso de faltar prueba literal, registra `venue_candidate`, `venue_candidate_basis`, `venue_profile_evidence_url` y `account_context`; **no fabrica venue** ni aprueba editorialmente. Roles de curador/artista itinerante y sedes `verified_internal` no permiten herencia automática. Igual ID de `Collector.add`; no cambió la fecha/hora.
- `tests/test_radar2_account_context.py`: 12 casos positivos y negativos (Teatro UNLP, Centro de Arte, Laura Gan, Cineclub Proyecciones Terrestres, Pura Vida, Espacio 44, Sindicato, Luti, fuera de sede, cuenta desconocida, estabilidad de ID y Meta sin token).

**Pruebas ejecutadas en sandbox aislado:** suite integral **548 pruebas, 547 aprobadas y 1 omitida**, cero fallos. La relectura de ocho publicaciones originales produjo **6 propuestas con sede y 9 candidatas**. Ampliación a **31 documentos originales / 45 propuestas que antes carecían de venue**: `RESOLVED=6`, `CANDIDATE=11`, `UNRESOLVED=28`, `ID_NOT_RECOVERED=0`, **0 cambios de fecha/hora**. Detalle por perfil: `@proyeccionesterrestres` 3, `@teatrounlp` 1, `@centrodearteunlp` 1, `@lauraganceramica` 1 resueltos. Candidatas: Pura Vida 5, Centro de Arte 2, Teatro UNLP 1, Museo de Arte y Memoria 1, Patio Café 1, Espacio 44 1. Los seis de Luti y seis de Sindicato permanecen sin inferir sede, correctamente conservadores.

**Importante:** la medición fue **en memoria con originales de Neon**, no reescritura de Neon ni prueba de funcionamiento diario. El corte guardado aún refleja los 45 faltantes anteriores. **NO GO para certificado de recuperación ni 10/10**: requiere replay versionado controlado + readback/idempotencia tras la corrida programada o ensayo autorizado, y un holdout independiente no utilizado para el desarrollo.

**Siguiente lote focalizado:** enriquecer perfiles no identificados de la rotación (Ópera, Teatro de Cámara City Bell, Sala 420, etc.) mediante web/identidades corroboradas; resolver fuentes cruzadas para eventos concretos (Yuna soy yo ↔ El Día, La Nona ↔ TeatroCerca, Josefina Ignisci ↔ Genda); segmentación segura de agendas Pura Vida; identificar ciudad/medio en anuncios itinerantes; medir falsos positivos antes de cualquier admisión al catálogo oficial. El aumento de cobertura de perfil **no** implica más scraping de Instagram ni acceso privado extra.

---

## Instagram · seis casos reales de sede sin resolver — 07/11/2026

**Diagnóstico de lectura y ejecución aislada, sin reescribir Neon ni parser:** 68 candidatos Instagram en ventana 07–22/11; 45 sin sede, **45/45 con cuenta de origen identificada**, 39 con `caption-v2.3` y 6 propuestas de curaduría con `compound-v1`. Un cruce estricto cuenta↔`official_url` de **sede aprobada** identifica **12 registros** con vínculo verificable al perfil (no significa 12 eventos automáticamente ubicables). La reejecución del intérprete sobre **8 originales conservados** devolvió **0 sedes**; el defecto existe en el código actual.

**Causas:** catálogo `accounts.json` reducido, match textual de nombre/sede con espacios, regex limitada a `en ` y `📍` (omite `📌` o línea autónoma), ausencia de conciliación cuenta↔entidad `venue` y función↔otras fuentes; programas compuestos generan títulos genéricos. **No asignar siempre la sede de la cuenta:** Pura Vida y teatros requieren contexto, y Sindicato Argentino de Boleros anuncia ciudades y medios distintos. No clasificar shows online como presenciales.

**Evidencia y propuesta acotada:** [auditoría de seis casos + control negativo](https://github.com/diegomontenegroext-hash/poraca-explorador/blob/main/radar2/evidence/instagram-venue-six-case-audit-20261107.md). Resolver con evidencia literal, cuenta de sala previamente validada, alias y cruce independiente por título/fecha/función; conservar `venue_basis`, incertidumbre e ID. Replay exacto, pruebas independientes, idempotencia y no aprobación automática.

**Estado: NO IMPLEMENTADO**. Este es el siguiente defecto semántico de alto impacto. Categorías El Día/Genda corregidas previamente siguen intactas.

---

## Cierre de corrección de categorías — 07/11/2026 · ejecución real en Neon

**GO para clasificación corregida en este lote; no certifica autonomía ni curaduría.**

- **El Día, 06/11:** comparación sin escritura de `compound-v1.2` contra documento original de Neon: **88/88 IDs** iguales, **0 diferencias de título/fecha/hora/sede**. Se actualizaron **33 categorías** con guardia exacta y auditoría de `previous`/`corrected` en `evidence.category_revision`, preservando historia mediante el trigger existente.
- **Genda:** normalizador de etiquetas en `radar2/collector.py` para nuevas adquisiciones, incluida `Charla` y cuentas regresivas. Revisión de 144 propuestas guardadas de 17 documentos: **62 categorías históricas normalizadas**, **0 etiquetas no canónicas y 0 cuentas regresivas restantes**, guardando el texto original.
- **Integridad:** Neon **974 documentos, 1.781 propuestas, 6.635 versiones**; ninguna nueva propuesta ni aprobación editorial (0), **95 correcciones** en total, sin discrepancias de auditoría.
- **QA:** suite completa `python3 -m unittest discover -s tests -q` ejecutada desde sandbox aislado con checkout de `main`: **536 pruebas, 535 aprobadas, 1 omitida, 0 fallos**. La reserva El Día conserva 88 actividades.
- **Evidencia:** [acta JSON de replay](https://github.com/diegomontenegroext-hash/poraca-explorador/blob/main/radar2/evidence/category-replay-20261107.json) · [regresión sobre original](https://github.com/diegomontenegroext-hash/poraca-explorador/blob/main/radar2/evidence/category-regression-20261107.json).

**Queda abierto solo lo no demostrado:** QA editorial independiente de precisión/recuperación y roles en fuentes variadas; continuidad natural varios días; conciliación y curaduría de candidatos al catálogo de Por Acá. No ejecutar nueva FULL ni resetear Neon para validar una reclasificación ya comprobada.

---

## Terminación técnica — compound-v1.1

Código publicado en [`32b7ec4c`](https://github.com/diegomontenegroext-hash/poraca-explorador/commit/32b7ec4c53bdd9ae7507a89411fd7668ef51d750). **GO condicionado para uso privado; certificación integral no demostrada.**

- [x] Dos omisiones narrativas corregidas: agenda El Día 01/11 **21 → 23 actividades**. Cierre coral 17:45; `Versos de mi pago` sin horario inventado.
- [x] Programa padre, relación observada, evidencia literal y sede contextual consultables por API v1; ambas propuestas HTTP 200, históricas y no aprobadas.
- [x] Reprocesamiento de un original guardado, cero adquisiciones; 23 propuestas releídas, repetición con cero altas de nodos/relaciones. Interrupción HTTP 403 documentada y recuperada; última corrida concilió tres alias con baseline completo.
- [x] 533 pruebas técnicas, una omitida. 974 originales/1054 versiones preservados; 1781 propuestas/6540 versiones al corte; cero originales sin versión, padres colgantes o autoaprobaciones. SSO all habilitado.

[Acta final única, diez respuestas y evidencias](https://github.com/diegomontenegroext-hash/poraca-explorador/blob/main/radar2/COMPOUND_FINAL_20261107.md#acta-final-de-terminación--compound-v11-07112026).

**Siguen abiertos:** evaluación editorial suficientemente independiente y humana; fronteras título/sede, roles y descartes no completamente auditados; continuidad y cadencia en varios días naturales. Meta conserva renovación humana y alertas preventivas; no constituye autonomía completa de credenciales. Metas del mandato: precisión ≥95%, recuperación ≥90%.

---
## Resultado de la misión ejecutada — fuentes compuestas

**Código implementado y datos comprobados; NO GO para certificar capacidad integral 95%/90%/95%.** El issue sigue abierto por obligaciones editoriales concretas, no por ausencia de implementación.

[Informe final A–G, matriz, pruebas y límites](https://github.com/diegomontenegroext-hash/poraca-explorador/blob/main/radar2/COMPOUND_FINAL_20261107.md).
Código de interpretación `f7b5155`; límites/caché/consulta final `2c346ca`; cierre/evidencia en main `402bb641ac8484cea44f0365c926b3b94d82233d`. Intérpretes compound-v1 / caption-v2.3.

### Resuelto y demostrado
- El Día 06/11: una propuesta genérica → **88 actividades/funciones**, 86 con fecha/hora/sede.
- 0221 05/11 y 06/11: una genérica por nota → **42 y 33 actividades**, 38 y 29 con esos campos.
- Luti DfVEIVTSTGu, DfDGyw_SkDA y DeXYqWISZod: **16, 13 y 10 unidades** con títulos y lugares locales, sin horarios supuestos. La última conserva dos fechas explícitas y un programa multisede.
- Curador separado de organizador: recommended_by y procedencia; noticias secundarias; coincidencias entre fuentes pendientes de revisión. Las reseñas permanentes no crean eventos fechados.
- Recuperación de **11 originales**, 318 propuestas escritas/releídas, **cero adquisiciones** para recuperar; repetición idempotente, 78 alias preservados, cero altas de nodos/relaciones en esa repetición.
- [FULL + incremental reales, Actions 42332669232 SUCCESS](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42332669232). FULL: 641 documentos/1073 propuestas procesadas y siete errores de fuente visibles; incremental: 28/95, cero errores. Meta: 11 y 1 consultas reales; no se afirmó una tanda de diez donde hubo una.
- Corregido alcance heredado: incremental Genda **un día**; FULL siete. [Validación final 42333406637 SUCCESS](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42333406637): una página Genda, cero Meta por no haber cuentas pendientes, 10 documentos/35 propuestas y readback correcto.
- API protegida 200 para propuestas, programa multisede y recommended_by. Se corrigió un 503 de relaciones mediante materialización por consulta; **3621 registros idénticos en clon antes/después**, sin tabla/servicio/cron ni permisos nuevos.
- Regresión: 89 registros Genda y ocho TeatroCerca conservados sin cambios de campos; Guajira, tres películas y tres funciones conservan sus resultados. 529 pruebas locales, una omitida. SSO all/READY conservados.
- Inventario final: 974 documentos/1054 versiones, 1779 propuestas/6468 versiones; cero originales sin versión, referencias colgantes o autoaprobaciones.

La primera aceptación 42332441662 falló antes de adquisición/persistencia por mezclar evidencia textual con JSON. Se reprodujo, corrigió y agregó regresión antes de repetir. No se oculta ese fallo ni el 503 inicial.

### Obligaciones pendientes para cerrar
1. **Calidad integral independiente:** diez muestras de campos coinciden, pero la anotación es del agente, parcial y sin validación humana. No se demuestran aún precisión de ocurrencias ≥95% y recuperación ≥90%, con exactitud de campos críticos medida por separado en una muestra suficientemente representativa. No se certifica cero fusiones incorrectas en todo el corpus. Descartes de bloques no tienen un contador semántico completo.
2. **Continuidad/cadencia:** políticas implementadas en los tres horarios existentes; ventana curatorial adicional miércoles-viernes y rendimiento durante días naturales todavía no observados. No confundir corridas manuales con continuidad.

**No abrir otro backlog. No cerrar este issue por número de propuestas o tests.** El motor privado mantiene su GO condicionado anterior; la certificación integral de fuentes compuestas permanece NO GO.

---
## Investigación previa conservada como antecedente
Las restricciones de coordinación que siguen pertenecen a la investigación anterior. La misión posterior del propietario autorizó la implementación sobre main una vez concluida la intervención precedente.

## Hallazgo verificado (06/11/2026 ART) — SOLO BACKLOG, no implementar mientras Work interviene Radar 2

**Alcance:** mejora puntual de descubrimiento metódico y desagregación de las agendas periodísticas de El Día y 0221. Conservar arquitectura, esquema `radar2`, ledger, cron, estados editoriales, fuentes originales, API y rama `main`. **No modificar código ni ejecutar Radar por este issue hasta coordinar con la intervención de Work en curso.**

### Evidencia pública y patrón
- El Día publica cartelera del fin de semana en notas nuevas dentro de `/espectaculos`, con títulos y rutas variables. Confirmadas ediciones del 16/10, 23/10 y 06/11 (esta última publicada el viernes a las **01:11 ART**) y una agenda del domingo 01/11. URL testigo: https://www.eldia.com/espectaculos/agenda-espectaculos_1793938267
- 0221 tiene sección fija https://www.0221.com.ar/que-hago y artículos de «agenda cultural» jueves 05/11 y viernes 06/11: https://www.0221.com.ar/que-hago/sandra-mihanovich-la-plata-muerde-y-los-espiritus-la-agenda-cultural-la-plata-n136923 y https://www.0221.com.ar/que-hago/festival-la-cerveza-mmce-y-piazzolla-piano-la-agenda-cultural-la-plata-n136995
- Propuesta: vigilar explícitamente **jueves y viernes**, repasar fin de semana, localizar las notas recientes por título/slug/contenido sin depender de un permalink constante; priorizar agenda sobre notas sueltas y no limitarse a la posición accidental entre las primeras seis entradas.

### Lo que ya hace Radar 2 (NO duplicar)
- En `radar2/collector.py`, `Collector.media_sources()` visita `https://www.0221.com.ar/que-hago` y `https://www.eldia.com/espectaculos`; filtra hasta seis enlaces y lee artículos con `document_lead()`.
- `radar2/actions_pilot.py`: la FULL llama `media_sources()`, pero las incrementales consultan Genda, no esta fuente específica.
- Lectura SELECT en Neon (`frosty-union-52906378`, rama `br-mute-recipe-b4odj2bl`, esquema `radar2`): las tres URL testigo están en `radar2.documents`, incluida la de El Día del 06/11 (último run `radar2-ghpilot-42326736932-attempt1`).
- **Defecto de extracción probado:** cada una de las tres notas genera **una sola propuesta no fechada, sin hora ni sede** en `radar2.proposals`; por ejemplo la nota de El Día, pese a enumerar decenas de espectáculos con días, horarios y lugares. El fallo principal NO es ausencia de adquisición de esos tres artículos; es falta de desagregación a ocurrencias.
- `document_lead()` preserva el artículo entero como un solo lead; los eventos internos no se convierten en candidatos individualizados. No confundir artículo capturado con función estructurada.

### Mejora acotada sugerida para una futura iteración
1. Garantizar detección focalizada de **agenda de espectáculos** (El Día) y **agenda cultural** (0221), con chequeo explícito jueves y viernes, más revisión liviana del fin de semana. Detectar cambios por URL/publicación/hash. No crear otro cron ni otro recolector.
2. **Desagregar cada edición** por día editorial (`Hoy`, `Mañana`, `Domingo`, `Sábado`, encabezados equivalentes) y sección (teatro, música, cine, talleres, literarias, fiestas, etc.) en propuestas de actuación individual: título, fecha real, horario, sede, categoría, `document_url`, bloque de evidencia. Distinguir funciones de una obra recurrente y recitales colectivos con varios artistas. No inventar faltantes.
3. Conciliar por título/fecha/hora/sede y evidencia contra Agenda La Plata, Alternativa, fuentes organizadoras, 0221/El Día e Instagram; conservar notas originales, procedencia y versionado; preservar el estado **no aprobado** de las propuestas periodísticas, sin publicar automáticamente.
4. Marcar las agendas periodísticas como **fuentes secundarias de descubrimiento y contraste**, sujetas a depuración; promover organizador/sala/ticketera original cuando haya respaldo. Tratar cambios/cancelaciones con incertidumbre explícita.
5. QA de regresión con estas tres URL reales: comprobar que se identifican varias actividades individualizadas con fechas y sedes correctas cuando están impresas; comparar con conteo manual de una muestra y probar idempotencia/dedupe entre publicaciones sucesivas. Dejar métricas de artículos hallados vs. funciones extraídas vs. corroboradas (sin declarar 10/10 automáticamente).

**Prioridad editorial:** alta para cobertura cultural; ejecutar después de que Work termine su intervención simultánea. No hacer reset de Neon, cambios de esquema ni despliegues por este ticket.

---

## Ampliación verificada: Instagram @lutitravelguide — agenda curada multipropuesta (06/11/2026 ART)

**Mismo problema semántico de fondo que las carteleras, con canal/cadencia distintos.** No abrir otro Radar ni interpretar un reel como un único evento. Este punto se suma a la misión focalizada de desagregación de fuentes curatoriales.

### Qué ya está funcionando (evitar duplicaciones)
- `radar2/instagram_official_pilot.py`: `lutitravelguide` es uno de los **4 controles fijos**, incluido en la FULL diaria (`include_controls=True`) y consulta hasta 12 medios mediante Meta Business Discovery. Las incrementales usan `include_controls=False`: **Luti no tiene una consulta específica fija por la tarde/noche**.
- `radar2/rotation.py`: Luti además está en `PRIORITY`; `radar2/accounts.json` la clasifica como curaduría y `radar2/instagram_roster.json` como curadora.
- **Lectura real de Neon, solo SELECT:** 12 documentos oficiales de esa cuenta en `radar2.documents` (`payload.profile_username='lutitravelguide'`), de ellos 10 videos, publicaciones 11/10 a 06/11. Las 12 propuestas fechadas de estas publicaciones corresponden a solo cuatro posts, no necesariamente 12 eventos distintos bien identificados.
- Captions recuperados correctamente; el adaptador oficial almacena **texto de caption**, permalink, ID, tipo y hora de publicación, **no demuestra haber leído transcripción/audio/frames del video**.

### Prueba inequívoca de falta de desagregación y atribución
1. Reel 04/11: https://www.instagram.com/reel/DfVEIVTSTGu/ . Su caption (almacenada en Neon) enumera actividades de miércoles, jueves, viernes, sábado y domingo, incluyendo Noche de las Librerías Platenses, Freezer Fotofest, fiestas cerveceras, Ópera, Open House La Plata, Feria Entramadas, etc. `radar2.proposals` contiene **una única propuesta fechada (07/11), sin sede**, titulada con el encabezado general. Hay eventos sin individualizar.
2. Reel 28/10: https://www.instagram.com/reel/DfDGyw_SkDA/ . El caption contiene varias actividades por días, pero quedó **sin propuestas fechadas**.
3. Reel 11/10: https://www.instagram.com/reel/DeXYqWISZod/ . El parser generó **9 propuestas fechadas**, pero con **el mismo título global y la misma sede 'Ciudad de Gatos'** para todas. No confundir reconocimiento de fechas con identificación de funciones/lugares; es un **riesgo de falsos enlaces y falsa confianza**.
4. Otros reels son reseñas de bares o viajes y no eventos: no convertir automáticamente cada mención en evento futuro (ej. reel 06/11 sobre café en Ruta 2).

### Causa funcional observable
- `radar2/caption.py` (`caption-v1`) extrae fechas del caption completo y usa el primer título global; el lugar se elige globalmente del texto completo y se reutiliza en todos los bloques. No comprende bien listas organizadas por encabezados de día sin día/mes explícitos, ni la relación local **recomendación -> día -> actividad -> sede -> organizador**.
- En propuestas multi-evento puede repetir nombre/lugar de toda la publicación; también pierde publicaciones tipo 'miércoles:', 'jueves:' sin fechas numéricas.

### Corrección acotada para Work al terminar la intervención vigente
1. Tipificar `lutitravelguide` como **fuente curadora / multi-evento**, diferente de organizador, sala o artista; identificar posts `agenda semanal`, `recomendación de lugar`, `reseña histórica` y `viaje externo`. Usar su autoridad de descubrimiento, no elevar a corroboración oficial ni autopublicar.
2. Parsear **bloques por día y actividad** (incluyendo enumeraciones sin números, 'jueves:', 'sábado y domingo:', 'desde el viernes...', fecha explícita y relativa) anclados a la **fecha de publicación en ART**. Devolver una propuesta por actividad/función identificable con evidencia exacta, dejando fecha, horario o sede en null si no hay sustento.
3. Atribuir **título, lugar y cuenta organizadora por bloque**, no globalmente. Eliminar el patrón de nueve actividades todas con el mismo título/sede equivocada. No deduplicar solo por fecha: puede haber muchas actividades el mismo día; una misma actividad puede tener varias fechas.
4. Cruzar enlaces/mentions con fuentes originales (salas, organizadores, carteleras, ticketing) y memoria cultural Neon. Preservar reel como documento fuente y las recomendaciones individuales como propuestas versionadas no aprobadas.
5. **Prioridad de revisión:** mantener control FULL diario y evaluar revisión adicional en **incrementales de miércoles, jueves y viernes**, sin cron extra, solo si hay nuevo media ID o cambios; respetar cuota/rotación Meta y contabilizar consultas efectivas. No repetir indiscriminadamente la lectura de las mismas 12 publicaciones.
6. QA con estos 3 captions reales más un reel de reseña no-evento. Etiquetar manualmente unidades de recomendación y comprobar recall, asignación correcta de título/día/lugar, falsos positivos, no duplicación entre varios posts, cobertura de eventos reales vs. documentos leídos. Reportar casos ambiguos y límites: **no afirmar transcripción ni lectura visual del video** solo por disponer de caption.

**Estado:** únicamente backlog/documentación. **NO modificar** `radar2/`, `main`, cron, Actions, Neon ni Vercel en esta revisión; Work continúa su misión actual.
