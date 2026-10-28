# RADAR DEFINITIVO — Contrato de operación 0.1

**Fecha:** 28/10/2026. **Estado:** ejecutor independiente de GitHub Actions con código, fuente y esquema propios. NO es todavía el Radar canónico de Por Acá ni reemplaza ChatGPT Radar.

## Separación
- **Repositorio GitHub:** `diegomontenegroext-hash/poraca-explorador`. No se creó otro repositorio: el conector actual no expone una acción de creación de repositorios, de modo que se creó un **workflow y motor independientes dentro del existente**, sin modificar el piloto.
- **Código:** `src/radar_definitivo.py`; pruebas `tests/test_radar_definitivo.py`.
- **Workflow:** `.github/workflows/radar-definitivo.yml`, distinto de `radar-paralelo.yml`; concurrency propia para evitar duplicaciones internas.
- **Neon:** proyecto `frosty-union-52906378`, rama `br-mute-recipe-b4odj2bl`, base ya protegida por nombre/rol `poraca_explorador`, **schema independiente `radar_definitivo`**. Tablas exclusivas `sources`, `runs`, `source_checks`, `candidates`, `candidate_sources`, `entities`.
- **Acceso:** mismo secret cifrado de GitHub `NEON_EXPLORADOR_DATABASE_URL` ya validado; nunca almacenado en el repositorio. Verificación exacta de database, role y existencia de schema antes de escribir.
- **No** tocar `neondb`, Motor, Puente, API, Vercel ni la tarea ChatGPT Radar.

## Fuentes reales: inventario y capacidad
Se migraron exclusivamente **nombres/URLs públicas y papeles de fuente** desde la investigación histórica de Radar a una nueva tabla experimental.
- **63 webs/servicios habilitados para adquisición** (`monitoring_mode='fetch'`).
- **39 URL web históricas en revisión** (`monitoring_mode='review'`), por ejemplo páginas de una única actividad, entradas antiguas y otras que no conviene monitorear permanentemente.
- **123 cuentas reales de Instagram** (`monitoring_mode='discover_only'`) del catálogo histórico `radar_lab_sources`: Guajira, Luti, La Selva Yoga y otras. Tres registros antiguos `research-...` no eran handles válidos, por eso no se convirtieron en perfiles públicos.
- **123 perfiles candidatos como fuentes culturales** en tabla `entities`, sin presumir que representan eventos o artistas nuevos.
- El programa *no intenta leer en masa los 123 perfiles*, dado que las raíces de perfiles devuelven frecuentemente 429. Detecta URL exactas de `/p/` y `/reel/` en agendas y artículos y prueba sus metadatos públicos con presupuesto y parada por 429. No ve Stories ni realiza login.

## Dos modos de ejecución
**FULL:** selecciona hasta 36 webs habilitadas que menos recientemente se revisaron, priorizando las nunca revisadas. Hasta 8 detalles por web y hasta 2 permalinks exactos Instagram enlazados dentro de cada detalle. La cobertura de las 63 webs necesita *al menos dos lotes* si todas son accesibles y no hay límites; FULL no equivale a certificar todas las fuentes de una vez.

**INCREMENTAL:** selecciona hasta 36 webs con `next_due_at <= now()`, máximo 4 detalles por fuente. Guarda `last_checked_at`, siguiente fecha según `cadence_hours`, razón de fallos y backoff. Misma URL repetida no crea candidato duplicado. Se actualizan los metadatos cuando se logró nueva lectura. En ambos modos se guarda cada fuente como transacción independiente para conservar progreso frente a errores.

**Presupuestos por corrida:** 19 minutos de adquisición, 30 minutos del workflow GitHub, máximo 200 solicitudes HTTP, 18 solicitudes a posts Instagram, 24 solicitudes por host y pausa mínima entre solicitudes. Un 429 bloquea ese dominio para el resto de la corrida; sin proxies, scraping autenticado ni evasión de límites. Los horarios de GitHub son aproximados.

## Qué se guarda y qué NO
- Run: inicio, fin, modo, cantidad de fuentes seleccionadas/revisadas, aperturas, links hallados, URLs candidatas nuevas y observadas, posibles entidades, estado parcial/completo.
- Por fuente: HTTP, detalles abiertos, errores, próximo control, fallos consecutivos.
- Por candidato: URL, tipo de ficha, título/descripción corta, fecha/hora/sede/organizador **cuando existan explícitos**, metadatos y procedencia y fuentes que corroboraron.
- Entidades candidatas a partir de nombres *explícitos* en JSON-LD Event (organizador/sede). Todas quedan en `review_state='candidate'`.
- **No guarda HTML completo, contenidos privados, Stories ni fotografías descargadas.** No aceptan ni publica eventos nuevos automáticamente.
- **No equiparar** número de URLs con eventos, ni fuente social catalogada con cuenta efectivamente leída. Las imágenes deberán tener un procedimiento de procedencia independiente.

## Verificación operativa en Neon

```sql
SELECT run_id,mode,started_at,finished_at,status,sources_selected,
       sources_checked,sources_success,urls_discovered,candidates_new,
       candidates_seen,entities_new,summary
FROM radar_definitivo.runs ORDER BY started_at DESC LIMIT 10;

SELECT kind,monitoring_mode,count(*) FROM radar_definitivo.sources GROUP BY 1,2;
SELECT kind,review_state,count(*) FROM radar_definitivo.candidates GROUP BY 1,2;
SELECT status,count(*) FROM radar_definitivo.source_checks GROUP BY 1;
SELECT source_id,name,last_checked_at,next_due_at,last_status
FROM radar_definitivo.sources WHERE monitoring_mode='fetch'
ORDER BY last_checked_at NULLS FIRST,priority DESC LIMIT 30;
```

## Próxima etapa de excelencia
1. Confirmar una corrida real de GitHub, readback en Neon y revisar fuente por fuente resultados sin inventar éxitos.
2. Completar reconocimiento de más formatos (RSS, Atom, sitemaps, JSON-LD diversos, calendarios por día), autores y imágenes, categorías y circuitos.
3. Recoger Instagram desde más agendas que enlacen publicaciones; validar si existe un camino público no intrusivo para perfiles y medir su rendimiento.
4. Identificar recencia, fechas de cada función/ciclo, lugares, artistas y causas de conflictos. Aún no hay equivalencia semántica con Motor 5.2.
5. Reconciliar duplicados entre Neon experimental y operativa y diseñar promoción sólo de datos verificados y revisados, antes de sustituir el Radar ChatGPT.

El nombre **Definitivo** expresa la arquitectura objetivo, no una certificación de cobertura total alcanzada.
