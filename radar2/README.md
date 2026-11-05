# Radar 2 — adquisición cultural con alcance limitado

Estado al 05/11/2026 UTC: **GO LIMITADO**, no GO de inteligencia autónoma de Instagram. Se conserva Radar 2 y el esquema existente. No se añade un recolector, workflow ni cron. La tarea activa del propietario ejecuta las búsquedas con sus herramientas autenticadas; Python consume el manifiesto resultante. No hay API de búsqueda gratuita universal incorporada al ejecutable Python.

## Ejecución ordinaria

1. En el ejecutor existente, cargar `radar2/search_discovery.js` y ejecutar `discoverCulturalWeb(tools)`. Guardar su resultado JSON como `search.json`. Son 14 consultas con mes/año argentinos y referentes culturales; ninguna URL individual de evento es entrada humana. Para una ventana incremental puede pasarse `options.queries` con un subconjunto de cuatro consultas. Los resultados vacíos y fallidos se conservan.
2. Leer el inventario actual de `radar2.private_discoveries` con el lector `poraca_motor_qa` y guardarlo como `baseline.json`. Una copia anterior de `result.json` es opcional y acelera relecturas. No importar observaciones antiguas como hallazgos nuevos.
3. Ejecutar el mismo código probado:

```sh
python3 radar2/collector.py --out /ruta/privada/corrida --discovery /ruta/privada/search.json --baseline /ruta/privada/baseline.json
RADAR2_CONNECTION_FILE=/ruta/privada/conexion.json python3 radar2/persist.py /ruta/privada/corrida/result.json
```

La conexión contiene `{"url":"postgresql://..."}` exclusivamente del escritor existente `poraca_radar_limited_prod`, fuera del repositorio, permisos 600. No usar owner ni elevar permisos. `persist.py` verifica rol/proyecto/rama, parametriza los datos y hace upsert sin DELETE. La vista existente deduplica y conserva las evidencias de alias. `--legacy-baseline` permite descontar conocimiento anterior para una evaluación, nunca para adquirirlo. Las marcas de conocimiento previo se conservan al repetir escrituras.

Genda siempre lee siete días desde la fecha argentina. `--start YYYY-MM-DD` reproduce una ventana declarada; el 50/50 de noviembre 4–10 no certifica otras semanas. `--previous` reutiliza extracción solo si contenido y versiones del colector/intérprete no cambiaron. `--web` conserva las capacidades anteriores, no es imprescindible para el descubrimiento abierto.

Las consultas descubren documentos públicos; el colector respeta robots y bloqueos, limita cuerpos y enlaces por página, extrae JSON-LD Event y anuncios individuales delimitados por secciones. Convierte UTC a Argentina, nunca usa datePublished como fecha del evento y conserva nulos. Artículos no interpretados permanecen documentos para investigar, no eventos confirmados. Las relaciones con cuentas se apoyan en nombres/sedes explícitos, no en supuesta autoría de Instagram.

## Consulta y límites

`https://poraca-lp-privado.vercel.app/api/radar2?format=html&discovered=1` muestra candidatos procedentes de búsqueda; `&id=ID` enlaza una propuesta concreta. Hay fuentes, estados, organizadores y vínculos culturales cuando se conocen. Noindex, SSO y lector sin INSERT permanecen activos. Es una consulta de staging; no una promoción al canónico.

`accounts.json` conserva veinte referentes y Nómade ambiguo. `instagram.py` es experimental: requiere META_IG_USER_ID, META_ACCESS_TOKEN y META_GRAPH_VERSION reales. No fueron proporcionados ni se probó Business Discovery. **Cero publicaciones directas autorizadas en esta intervención.** No se usa Instagram HTML, proxies, oEmbed como descubridor ni proveedores pagos.

Las ventanas ordinarias pertenecen a una sola tarea ya activa, actualizada en su lugar. Sus próximas ejecuciones naturales no fueron observadas en esta intervención. La operación depende del acceso del ejecutor a búsqueda, GitHub, Python y Neon; ante ausencia debe informar bloqueo, no afirmar éxito ni usar otro Radar. No crear tareas ni reactivar las pausadas.

Informe y resultados: `docs/RADAR2_20261104.md`. Los datos públicos son hechos, IDs, consultas, hashes y referencias; no se publican capturas integrales ni secretos.

## Paneo rotativo del índice público (05/11/2026)

`instagram_roster.json` conserva los **123 handles válidos** del padrón
`public.radar_lab_sources` (126 referencias: tres `research-*` no son usuarios).
Los 20 referentes de `accounts.json` se conservan también. No se fusionan
identidades ambiguas ni se presupone que los 123 sean cuentas profesionales.

`rotation.py` usa una única fila de control reservada de `radar2.runs`,
`radar2-instagram-rotation-state-v1`, con tipo `instagram_rotation_control`.
**No es una corrida de adquisición y debe excluirse de sus contadores.**
No hay migración ni nuevos permisos: usa el escritor limitado existente.
Mantiene prioridad, revisiones, último intento, resultado por canal, próxima
revisión y lease de dos horas. Un CAS de versión protege frente a concurrencia;
el mismo run reutiliza su lote. Se revisan primero los menos revisados y, dentro
de esa vuelta, los referentes culturales prioritarios. No adelantar el cooldown:
24 horas para referentes con resultados, 72 para otros con resultados, 96 sin
resultados y 8 si falló la búsqueda. Las cuentas no revisadas no pierden turno.

En la misma tarea y ventana existente, después del preflight y del reclamo del
run ordinario, inicializar idempotentemente y reclamar como máximo diez:

```sh
RADAR2_CONNECTION_FILE=/privado/conexion.json python3 radar2/rotation.py init --out /privado/init.json
RADAR2_CONNECTION_FILE=/privado/conexion.json python3 radar2/rotation.py claim --run-id ID --out /privado/rotation.json
```

Cargar `rotation.json` y pasarlo como `options.rotation` a
`discoverCulturalWeb(tools, options)`; el resto de `options.queries` sigue igual.
Si `batch.status` ya es `completed`, no repetir el paneo de ese run. Cada cuenta
produce una consulta indexada de Instagram y otra de su red pública. Un filtro
de dominio comprueba que el enlace devuelto sea realmente Instagram: respuestas
externas del buscador no cuentan como publicaciones. Conserva resultados y
fallos; un fallo individual no corta el resto. Las exclusiones de espejos y la
prohibición de descarga directa de Instagram se conservan. La búsqueda ordinaria
ya no excluye Instagram.

El colector conserva únicamente el extracto indexado como documento investigable,
con alcance `search_excerpt_only`, fecha del evento nula y `direct_profile_read=false`.
No interpreta la fecha de indexación como fecha cultural ni atribuye autoría por
haber aparecido en una consulta. El camino HTTP existente procesa las fuentes
externas, con clasificación, vigencia y conciliación habituales. Las respuestas
ajenas al referente o sin contexto cultural se descartan antes de descargarlas.

Tras `persist.py` exitoso y lectura de control de las propuestas, finalizar el lote:

```sh
RADAR2_CONNECTION_FILE=/privado/conexion.json python3 radar2/rotation.py complete --run-id ID --manifest /privado/search.json --out /privado/reviewed.json
RADAR2_CONNECTION_FILE=/privado/conexion.json python3 radar2/rotation.py preview --out /privado/next.json
```

`complete` verifica que el run tenga persistencia completada. Conservar en el
summary del run el lote, cantidades, estado por canal, contexto de ejecución y
la evidencia de lectura. Si falla la rotación, informar el fallo y ejecutar el
resto de las fuentes: Instagram es una fase opcional. Un fallo del preflight
GENERAL de búsqueda/runtime sigue siendo un bloqueo real del ejecutor completo.
La API oficial sigue separada, deshabilitada sin credenciales Meta verificadas.
Ver `docs/RADAR2_INSTAGRAM_ROTATION_20261105.md` para resultados y límites reales.
