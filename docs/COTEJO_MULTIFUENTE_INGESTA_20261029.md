# Por Acá — cotejo de publicaciones múltiples en Radar · 29/10/2026

## Resultado de la auditoría por fuente

| Fuente | Captura | Sesiones individuales en staging | Evidencia / pendientes |
|---|---|---:|---|
| Luti Travel, reel 28/10 | caption completo, un solo `candidate` | 0 | curadora `discover_only`, publicación multiactividad aún sin descomposición |
| Genda (Agenda La Plata) | 11 checks, 7 `ok`, 4 `index_only` | **98** con fecha/hora/sede; 11 páginas de fecha | `secondary_agenda`, requiere vincular originales, no aceptar desde cartelera secundaria |
| Alpedó | 10 checks, 4 `ok`, 6 `index_only` | **160** con fecha/hora/sede; 4 páginas | `secondary_agenda`, mismo gate de originales |
| Alternativa Teatral | 13 checks, 9 `ok`, 4 `index_only` | **28** fechas/horarios en 10 URLs; **9 sin sede** en corte inicial | `primary_ticket_listing`, pero falta sede por sesión y evitar ciudades ajenas |
 
Datos obtenidos mediante SELECT Neon solo en `frosty-union-52906378 / br-mute-recipe-b4odj2bl / neondb` 29/10/2026. Los conteos son acumulados de staging, no eventos nuevos ni funciones aprobadas en web.

## Decisión de arquitectura

**El problema NO es uniforme en adquisición:** Genda/Alpedó/Alternativa ya son parseados a `listing_occurrences` con cada fecha y horario, conservando `source_id`, `proof_url`, `proof_method`, `evidence_tier` y `review_state=observed_unverified`. Luti, en cambio, permanece como un `candidate` con múltiples propuestas en una leyenda de Instagram. La solución útil consiste en un **contrato de evidencia y descomposición según el tipo de fuente**, no en un segundo Radar, ni crear 98 eventos públicos desde Genda.

**Brecha transversal a corregir:** las propuestas individuales necesitan una representación de su procedencia y un camino a sus originales. No confundir página contenedora de cartelera, URL directa de una obra, función con día/hora y original que corrobora sede/roles. Una cartelera secundaria es descubrimiento, no autorización de ingreso.

## Error concreto detectado: obra itinerante de Alternativa

El original de [Muerde](https://www.alternativateatral.com/obra72170-muerde) contenía una función del viernes **30/10, 21:00, en Muñiz**, y otra del domingo **01/11, 19:00, en Sala 420 de La Plata**. Antes, el Radar almacenaba dos funciones con `venue=NULL` para ese original; un intento de asignar globalmente «Sala 420» a toda la página habría publicado erróneamente Muñiz en La Plata. **Corrección de parser** en `src/radar_agenda_adapters.py`: ligar cada función al último bloque de localidad y sala explícitos antes de su fecha; rechazar las funciones explícitamente fuera de La Plata; preservar `NULL` si falta evidencia, nunca copiar sede futura ni histórica. Se añaden dos tests de regresión, sin modificar Neon histórico ni liberar gates.

## Siguientes acciones en la cadena existente

- **#28 Radar**: distinguir `post` curatorial, `listing` secundario, `obra` original y `function` individual; enlazar originales de Genda/Alpedó con cupos y fecha, no multiplicar por la URL diaria ni afirmar que 98 son verificadas. Registrar alertas de deriva `index_only`.
- **#10 Motor/gate**: verificar `title + date + clock + actual room + original source` antes de conciliar una función; respetar `HOLD_SECONDARY_SOURCE`, `HOLD_MISSING_VENUE`, `HOLD_MULTIPLE_EVIDENCE_FOR_SAME_FUNCTION` y no fusionar una obra con varias fechas o sedes.
- **#35 entidades**: al reconocer sede, vincular `hosted_at` solo tras aceptación, no atribuir `organized_by` ni inferir identidad por cartelera/ciudad. Mantener programa TACEC distinto de Sala Iris.
- **#7 continuidad**: readback de un primer original válido de staging hasta observación pendiente, solo tras autorización y permisos.
- **#16 maestro**: índice de criterios y falsos positivos.

No se crea esquema de Neon, cron ni Motor paralelo; no se ejecuta SQL de escritura ni publicación Vercel por cambio Radar. Mantener QA del workflow GitHub y confirmar próximo uso en una corrida programada, sin forzar recolección extra.

## Ajuste complementario: fuentes curadoras con varios planes en una leyenda

Se agregó `curator_multi_plan_preview()` en el Radar Definitivo. Para un permalink exacto de Instagram cuya fuente esté expresamente registrada con rol `curadora`, y solo si la leyenda trae 3+ líneas con cuentas mencionadas y al menos dos días de semana distintos, añade a `candidate.evidence.multi_plan_review` una lista acotada de **fragmentos literales y @cuentas**. El ejemplo de Luti produce 12 fragmentos **solo para revisión**. No infiere fechas, horas, sedes, roles de los participantes ni disciplinas, ni crea eventos o nuevas entidades. Esto funciona con el JSONB `evidence` existente, sin columnas ni ejecutores nuevos. Solo se aplica al capturar por enlace público exacto: no habilita recorrer perfiles de Instagram ni evade limitaciones de acceso. La prueba evita convertir un post con tres cuentas etiquetadas en tres funciones.

## Control incremental implementado: espejo vs original

A partir del próximo Radar programado, el resumen de cada corrida incluye `evidence_quality` calculado con **un SELECT de solo lectura sobre un máximo de 5000 listing_occurrences**. Resume registros con HTML de sede, faltantes, claves compartidas Genda/Alpedó y claves con ticketera original en URL **específica de evento** (no índices de cartelera). Se preserva el estado HOLD y 0 eventos promovidos. El control distingue la evidencia de título/fecha/hora/sede de múltiples fuentes secundarias del enlace a una obra original; aún en coincidencia exacta ese enlace solo es una **sugerencia de revisión**, no admisión. En el corte 29/10 se encontraron 51 sedes con fragmentos HTML en 160 históricos Alpedó, 57 claves repetidas entre Genda/Alpedó y coincidencias exactas con fichas *Juli Bellese* y *Epifanía* en fuentes originales; no reescribir el histórico. El reporte aparece en el resumen JSON/Actions del Radar ordinario, sin cron, consultas externas adicionales ni fuente de publicación nueva.
