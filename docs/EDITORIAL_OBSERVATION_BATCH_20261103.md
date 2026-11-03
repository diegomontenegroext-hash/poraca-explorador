# Puente editorial: lote controlado de El Ánimo — 03/11/2026

La única operación candidata del lote es el [SQL de observaciones internas](../sql/20261103_editorial_observation_safe_batch_v1.sql). No modifica agenda, no publica, no crea lugares ni relaciones canónicas.

**Preflight:** producción `br-mute-recipe-b4odj2bl` devuelve exactamente dos propuestas por ID, fechas **06/11** y **27/11** a las **21:00**, origen editor `src-alternativa-teatral` (no confundir con Radar `rd-web-3b2b6ade`) y sede admitida `en-eso-estamos`. Las dos fechas se corroboraron en el [original público](https://www.alternativateatral.com/obra103415-el-animo).

**QA:** `br-icy-night-b4larkc3` contiene ya dos observaciones equivalentes en HOLD, con `DO_NOT_APPROVE`, pero con antigua atribución al ID técnico Radar. Ejecución del mismo INSERT en QA devolvió **cero altas**, sin duplicar. No utilizar la rama QA como producción.

**Contrato:** seleccionar por IDs deterministas revisados; fuente editorial única por origen, sede `approved_public`, fuente fechada reciente y no un índice; no aceptar si ya existe observación equivalente o canónico; `ON CONFLICT DO NOTHING`; nueva observación `observed_unverified`, `matched_event_key=NULL`, `publication=DO_NOT_APPROVE` y `conflict=pending_editorial_handoff_review`. El escritor de eventos rechaza el conflicto: no existe promoción automática.

**Siguiente prueba:** ejecutar con rol editorial autorizado en producción solo tras QA y comprobar dos filas, sus IDs exactos, fecha/hora, origen, sede, bloqueo, y **cero** nuevos canónicos. Reejecución del mismo lote debería generar cero altas. La adquisición de Biblioteca UNLP y el gate F5 se miden aparte en FULL ordinaria.

**No elevar IICS por dos observaciones internas:** 5,2/10 hasta verificar decisión editorial y visibilidad real en API/web.
