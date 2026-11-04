# Radar · descubrimiento por día y programa, no por reloj
**Corte:** 03/11/2026. Cambio acotado a `src/radar_editorial_preview.py`, una consulta de solo lectura que agrupa candidatos para revisión.

## Contrato
- **Esencial:** título/acto o programa identificable, día anunciado, sede identificable en La Plata y alrededores, URL original HTTPS concreta y fuente primaria; sin fecha el registro es una actividad habitual/espacio, no una función fechada.
- **Optativo:** hora. Nunca reemplazar ausencia de hora por `20:00`, `00:00`, inicio supuesto de show, precio, duración ni cierre. Un mensaje «noche», «a partir de» o «aprox.» puede mostrarse como texto del original, pero NO como hora exacta ni valor para exportar .ics.
- **Identidad de una noche:** mismo título o programa + día en un origen; entradas múltiples de puertas y recital no deben producir duplicación automática. Si la fuente publica dos funciones genuinas del mismo espectáculo, la evidencia conserva ambos horarios y la bandeja señala `REVIEW_MULTIPLE_SLOTS_SAME_DAY`, sin auto-fusión de canónicos ni publicación.
- **Guardas fuertes:** fecha en original y sede identificable, discrepancias de sede, ticket accesorio, conflicto editorial previo, cancelación y posibilidad de duplicados. No convertir un índice genérico en fuente original de sesión y no cambiar el instante canónico para acomodar la búsqueda.
- **Salida:** sin escritura en Neon, sin promoción, sin modificación de fuente ni del contrato actual del writer. La previsualización incluye ahora casos sin HH:MM, conserva los avisos y deja a la edición autorizar cualquier alta.

## Evidencia del problema
Neon SELECT corte 03/11: 289 observaciones futuras, 13 sin hora válida; en el subconjunto de próximos 21 días con título, sede y original de clasificación primaria 86 observaciones, de las que **7** eran excluidas solo por falta de reloj. Este lote las vuelve **revisables**, no automáticamente publicables ni confirmadas.

## Lo siguiente, sin añadir capas
Revisar el punto exacto donde la `poraca_editorial_conversion_queue_v2` usa `MISSING_VERIFIED_START_TIME` (5 casos) y cómo el escritor opera con `event_time` nullable. Diseñar migración acotada solo tras QA de deduplicación por fecha + evento/sede + URL original, con escenarios de dos funciones genuinas en una tarde y una noche de cuatro bandas. No aprobar esas cinco automáticamente, especialmente índices sin original preciso o conflictos de fecha. Corregir después el copy del sitio si muestra hora aparentemente exacta sin ese respaldo.
