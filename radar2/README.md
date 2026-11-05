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
