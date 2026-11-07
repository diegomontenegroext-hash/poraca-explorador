# Radar 2 — estado operativo al 06/11/2026 ART

**GO OPERATIVO PARCIAL.** Adquisición de agendas, exploración de enlaces, rotación persistente, memoria cultural y Meta Business Discovery están ejecutándose en el workflow existente de GitHub. La primera consulta oficial exitosa (4 cuentas, 48 documentos) fue ampliada mediante rotación real a 14 cuentas consultadas, 118 documentos nuevos y 64 candidatos culturales adicionales: GitHub run #42324533672, SUCCESS; Neon readback confirmado. La deduplicación SQL preserva actualmente las 100 propuestas oficiales (en estado investigable). La corrida cron del 06/11 ocurrió antes de conectar Meta; la continuidad automática de varios días con Instagram aún no está certificada. No equivale a 100 eventos aprobados.

Acta verificable: [cierre de misión](../docs/RADAR2_FINAL_20261105.md). Evidencia estructurada: [certificación](evidence/final-certification-20261105.json). Los informes anteriores describen cortes históricos; la dependencia operativa de herramientas de Work fue sustituida por Python estándar dentro de GitHub.

## Ejecución existente

`.github/workflows/radar-definitivo.yml`, job `radar2_pilot`, ejecuta `actions_pilot.py`. Un solo cron: `27 8 * * *`, 05:27 ART. El legado permanece manual. La tarea anterior de ChatGPT no forma parte del nuevo ejecutor. No se creó otro workflow ni cron.

El secreto existente `NEON_RADAR_LIMITED_DATABASE_URL` pertenece a `poraca_radar_limited_prod`. El preflight comprueba rol, proyecto y rama antes de adquirir. No requiere paquetes Python, herramientas exclusivas de Work ni permisos sobre las tablas canónicas.

1. Recupera el inventario previo de `radar2.proposals` y documentos conocidos.
2. Adquiere las agendas y canales que ya funcionaban.
3. Reclama diez cuentas del padrón de 123 con CAS/lease en `rotation.py`.
4. Comprueba condiciones públicas de acceso de Instagram y disponibilidad del adaptador oficial. Un bloqueo nunca cuenta como publicación recuperada ni revisión exitosa.
5. Evalúa búsqueda RSS pública solo cuando robots lo permite. Bing la bloqueó en la prueba real: no existe búsqueda general productiva certificada.
6. Explora una frontera persistente de enlaces publicados por fuentes conocidas. Evalúa doce páginas como máximo por corrida diaria y dos por dominio. Rechaza enlaces técnicos, sociales, comerciales o sin contexto cultural local. Distingue candidatas, fuentes observadas productivas y monitoreo sostenido.
7. Interpreta anuncios y créditos explícitos, concilia alias y guarda evidencia con escritor limitado.
8. Enriquece el representante visible con los créditos de fuentes adicionales, conservándolos en sucesivas lecturas. La API privada existente devuelve los nodos y relaciones dentro de `entities`.
9. Relee ese mismo run desde Neon y guarda métricas históricas. Una salida técnica exitosa no equivale a aprobación editorial.

La confirmación experimental de dos lotes se hizo en un solo job; las correcciones posteriores releyeron únicamente la frontera, sin repetir la adquisición completa ni Instagram. El disparo de prueba queda en `ops/radar-fallback-trigger.txt`; sus opciones se ignoran en `schedule`. El cron siempre usa un lote y la adquisición diaria.

## Persistencia y límites

No hubo migración ni nuevos grants. Se reutilizan `runs`, `documents`, `proposals` y `private_discoveries`. Filas de control de `runs`, excluidas de las corridas de adquisición:

- `radar2-instagram-rotation-state-v1`: padrón, intentos, resultados, leases y próximas visitas.
- `radar2-source-discovery-state-v1`: enlaces candidatos, origen, revisión, vigencia y productividad.
- `radar2-cultural-memory-state-v1`: nodos, alias de identidad, relaciones y evidencia acumulada; staging, no catálogo canónico.

`review_count` conserva la revisión por buscador exitosa; `attempt_count` gobierna la rotación justa incluso ante bloqueos. `last_successful_post_at` solo se actualiza al obtener publicaciones. Se conserva el motivo y la huella de robots por cuenta. No se solicitan páginas de perfiles cuando existe restricción explícita ni se usan proxies, CAPTCHA o autenticación privada.

Al cierre histórico del 05/11 faltaban las credenciales Meta; fueron cargadas y probadas el 06/11. De las 123 cuentas del padrón se han probado 10 por el método oficial rotativo, todas con publicaciones, además de los cuatro controles fijos. La elegibilidad de las cuentas restantes aún no está acreditada. `META_IG_USER_ID`, `META_ACCESS_TOKEN` y `META_GRAPH_VERSION` siguen siendo requisitos del adaptador oficial, no servicios contratados o permisos ampliados por esta intervención.

Los documentos irrelevantes se archivan con `review_state=historico`, `kind=rejected_document` y razón explícita; esto usa el estado de archivo existente y no afirma que sean eventos pasados. Los precursores sin interpretar usan `kind=superseded_document`. Nada se borra.

Las fuentes con dos lecturas productivas tienen `extraction_verified_repeatedly`; `monitoring_certified` exige evidencia de productividad en dos días distintos. Las dos lecturas controladas de Lumen Artis no acreditan monitoreo sostenido.

## Verificación

```sh
python3 -m unittest discover -s tests -p 'test_radar2*.py' -v
python3 -m unittest discover -s tests -v
```

Al cierre: 483 pruebas, 482 aprobadas y una omitida. La prueba natural del cron, la continuidad de varios días y la adquisición de publicaciones de Instagram no están certificadas.

## Piloto Instagram oficial de cuatro cuentas — 06/11/2026

Se integró a la **misma corrida GitHub de las 05:27 ART**, sin crear tareas, ramas, cron ni servicios adicionales. Referentes fijos de comparación: `guajira.bar`, `lutitravelguide`, `escenario40`, `teatroargentinopba`. Código: `instagram_official_pilot.py`; pruebas offline: `tests/test_radar2_official_pilot.py`.

El piloto es **exclusivamente Meta Business Discovery**, no reproduce las peticiones HTTP HTML del experimento interactivo del 04/11 ni utiliza Chromium. Los resultados quedan diferenciados en `radar2.runs.summary.instagram_official_pilot` con estado, cuentas, cantidad de llamadas, documentos y candidatos. Las publicaciones verificables se registran únicamente en staging `investigable`, nunca como eventos automáticamente admitidos. Se omiten permalinks ya conocidos y se limita a 12 medios por cuenta. El 06/11 se verificó manualmente que la API devuelve cinco publicaciones de `teatroargentinopba` mediante Graph API Explorer; esa prueba externa no acredita aún extracción ni persistencia por GitHub. El adaptador se alineó con los campos probados (`username`, `id`, `caption`, `permalink`, `timestamp`).

Sin configurar `META_IG_USER_ID` y `META_ACCESS_TOKEN` en **GitHub Secrets**, y `META_GRAPH_VERSION` en **GitHub Variables**, el piloto guarda `NOT_CONFIGURED` y **realiza cero llamadas** a Meta. No se han suministrado esas credenciales ni se acreditaron permisos de terceros; por lo tanto, el próximo cron podrá verificar la integración, pero **no demostrará extracción Instagram** hasta completar el acceso oficial. Los 10 referentes que rotan diariamente siguen sirviendo para búsqueda de referencias web, pero sus comprobaciones no se confunden con las 4 consultas oficiales fijas. Fallos de Meta no detienen agendas ni fuentes web.

El método HTTP directo ejecutado desde GitHub sobre `guajira.bar` y `lutitravelguide` devolvió 429 en ambos casos en la prueba puntual. No se programa el reintento automático de ese método después de la restricción, aunque haya funcionado desde Work el 04/11.

## Actualizacion: rotacion oficial de Meta (06/11/2026)

El mismo workflow y horario 05:27 ART reutilizan el lote CAS/lease de 10 cuentas del padron de 123. Se consultan hasta 10 usuarios rotativos adicionales a los cuatro controles fijos; un handle repetido entre ambos se consulta solo una vez. Cada resultado individual se conserva en `summary.instagram_official_pilot` junto a los documentos y candidatos. Los nuevos anuncios se titulan con texto propio, no solo por el handle. Todas las propuestas permanecen `investigable`. La elegibilidad profesional se determina por respuesta oficial de Meta, no se supone para todo el padron. No se agregaron cron ni workflows.
