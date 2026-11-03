# Puente editorial: lote controlado de El Ánimo — 03/11/2026

La única operación candidata del lote es el [SQL de observaciones internas](../sql/20261103_editorial_observation_safe_batch_v1.sql). No modifica agenda, no publica, no crea lugares ni relaciones canónicas.

**Preflight:** producción `br-mute-recipe-b4odj2bl` devuelve exactamente dos propuestas por ID, fechas **06/11** y **27/11** a las **21:00**, origen editor `src-alternativa-teatral` (no confundir con Radar `rd-web-3b2b6ade`) y sede admitida `en-eso-estamos`. Las dos fechas se corroboraron en el [original público](https://www.alternativateatral.com/obra103415-el-animo).

**QA:** `br-icy-night-b4larkc3` contiene ya dos observaciones equivalentes en HOLD, con `DO_NOT_APPROVE`, pero con antigua atribución al ID técnico Radar. Ejecución del mismo INSERT en QA devolvió **cero altas**, sin duplicar. No utilizar la rama QA como producción.

**Contrato:** seleccionar por IDs deterministas revisados; fuente editorial única por origen, sede `approved_public`, fuente fechada reciente y no un índice; no aceptar si ya existe observación equivalente o canónico; `ON CONFLICT DO NOTHING`; nueva observación `observed_unverified`, `matched_event_key=NULL`, `publication=DO_NOT_APPROVE` y `conflict=pending_editorial_handoff_review`. El escritor de eventos rechaza el conflicto: no existe promoción automática.

**Siguiente prueba:** ejecutar con rol editorial autorizado en producción solo tras QA y comprobar dos filas, sus IDs exactos, fecha/hora, origen, sede, bloqueo, y **cero** nuevos canónicos. Reejecución del mismo lote debería generar cero altas. La adquisición de Biblioteca UNLP y el gate F5 se miden aparte en FULL ordinaria.

**No elevar IICS por dos observaciones internas:** 5,2/10 hasta verificar decisión editorial y visibilidad real en API/web.


## Ejecución realmente efectuada · 03/11 (posterior al QA)

- [CI #41698412185 SUCCESS](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41698412185): 428 tests, 1 skipped. Fallo intermedio #41698293744 causado únicamente por un test que contaba el prefijo de IDs también dentro del SQL integrado; se ajustó el alcance del test antes de ejecutar Neon de producción.
- La operación en Neon **QA** reinsertó **0** filas, porque ambas observaciones con esos IDs ya existían en HOLD. No se alteraron allí.
- La operación en Neon **producción** insertó **2 observaciones** exactas: `obs-stage-f416b398b13ad999fc693019` (06/11) y `obs-stage-780e4b6e4e4c424c457034f7` (27/11), ambas 21:00, `origin_source_id=src-alternativa-teatral`, `observed_venue=En Eso Estamos`, `reconciliation_state=observed_unverified` y `matched_event_key=NULL`.
- Readback independiente: dos observaciones exactas con `publication=DO_NOT_APPROVE`, `conflict=pending_editorial_handoff_review`; **0 canónicos nuevos** para estas fechas. La fila del 01/11 es histórica y no se confundió con estas dos.
- Sin publicación web, sin cron nuevo, sin nuevas ramas ni cambios de credenciales. Sigue faltando revisión editorial y eventual decisión expresa sobre cada función para su publicación.
