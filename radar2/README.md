# Radar 2 — prueba controlada de adquisición

Recolector mínimo de biblioteca estándar Python, almacenamiento aislado y consulta privada. Es un candidato experimental; no sustituye el proceso programado anterior porque el GO general no se alcanzó.

```sh
python3 radar2/collector.py --out /ruta/privada/corrida --web
python3 radar2/benchmark.py /ruta/privada/corrida
RADAR2_CONNECTION_FILE=/ruta/privada/conexion.json python3 radar2/persist.py /ruta/privada/corrida/result.json
```

La conexión JSON contiene `{"url":"postgresql://..."}` de **poraca_radar_limited_prod**, fuera del repositorio y con permisos de archivo 600. No utilizar una conexión owner. El escritor usa HTTPS de Neon y SQL parametrizado. La preparación única del esquema está en `schema.sql` y la conciliación visible en `reconcile.sql`; ya se aplicaron al entorno indicado en el informe. No volver a aplicar migraciones a ciegas.

Repetición con reutilización de extracción cuando el texto original no cambió:

```sh
python3 radar2/collector.py --out /ruta/privada/segunda --web --previous /ruta/privada/corrida/result.json
```

Genda siempre recorre siete días desde la fecha argentina de ejecución. `--start YYYY-MM-DD` existe para reproducir una ventana histórica declarada. La referencia congelada de noviembre no evalúa otras fechas.

`accounts.json` fija veinte referentes, incluido Nómade con identidad de handle pendiente. `instagram.py` contiene una implementación experimental de Business Discovery con Facebook Login. Sin `META_IG_USER_ID`, `META_ACCESS_TOKEN` y `META_GRAPH_VERSION` registra **no ejecutado**; no finge una consulta. No fue validado con credenciales. No hay scraper HTML de Instagram, extracción analítica de oEmbed, proxies ni proveedores contratados. Un token válido tampoco garantiza elegibilidad de todas las cuentas.

La respuesta privada se publica en el repositorio web como `api/radar2.js`. Noindex y Deployment Protection permanecen activos. El lector existente solo recibe SELECT sobre la vista, sin acceso a los documentos originales.

El manifiesto y el benchmark públicos contienen referencias y resultados. Las capturas originales, resultados completos y exportación de conocimiento están en el paquete privado entregado al propietario. No se publican secretos ni se importan datos anteriores como nuevos hallazgos.

Informe: `docs/RADAR2_20261104.md`. No se añadió ningún workflow ni cron.
