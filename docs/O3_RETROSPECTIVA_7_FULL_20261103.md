# Por Acá — O3 retrospectivo real, sin FULL adicional
**Corte:** 03/11/2026 · Fuentes: 7 últimas filas reales `radar_definitivo.runs` y sus `source_checks`, en Neon operacional, consultas exclusivamente SELECT. Congeladas en `data/o3_seven_full_backtest_20261103.json`.

## Respuesta operativa
- **7/7 FULL:** todas seleccionaron y persistieron sus chequeos. No hay deuda de chequeos dentro de la propia ejecución.
- **1/7** tiene estado persistido `complete`, **6/7** `partial`. Eso es O3 estricto: **FAIL**.
- **5/7** habrían pasado **solo** el control HTTP de adquisición con la semántica `poraca-health-v2` (incluye cuatro `health-v1` históricas con cero fallos). **No se reescribe ninguna FULL anterior**, no se suman puntos retrospectivos y no se transforma 5/7 en 6/7.
- **2 fallos HTTP 503** en dos FULL nuevas de `research-museo-pettoruti` (mismo dominio original). El mismo origen devolvió 200/`index_only` en una incremental intermedia, por lo que no se atribuye una falla permanente ni se elimina el origen del inventario para maquillar estabilidad.
- **227 chequeos `index_only`** en las 7 FULL: no errores de red, pero tampoco extracciones de sesiones. La brecha mayor no es la falla 503: es la ausencia de oferta fechada en **yoga 0/2** y **talleres 0/3**, y limitada cobertura **vinos 1/2** (ticket Feria Catar todavía editorialmente HOLD).
- Estos 7 datos ya permiten confirmar la causa sin lanzar otra FULL; lanzar una octava fuera de horario no habría comprobado ninguna recuperación nueva ni corregido las páginas sin fecha.

## Plan seguro sin crear servicios
**Tanda A — Investigación focal en originales:** Casa Yogi, Ermides y Casa Dionisio publican actividades **habituales** o clases semanales. Clasificarlas como actividades regulares, con canal de consulta, sin inventar fechas y sin exigirle al extractor que genere recitales. En vinos, revisar la [Noche de las Vinotecas 2026](https://lanochedelasvinotecas.com.ar/) (13/11, circuito nacional) para localizar **solo los puntos de La Plata**, y la [Feria Catar V](https://www.passline.com/eventos/feria-catar-v-edicion) (27/11, Gorina, identidad/ticketera editorial HOLD), sin convertir todas las sedes del país en agenda platense.
**Tanda B — Diagnóstico en las siguientes FULL normales:** separar por fuente `HTTP_FAILED`, `INDEX_ONLY_200`, `ORIGINAL_DATED`, `REGULAR_ACTIVITY_ONLY`, `DISCOVER_ONLY_NOT_FETCHED`. Una FULL `complete` exige también todos los controles y persistencia; no es sinónimo de cobertura social completa. Comparar nombres de origen y prueba URL original entre fechas, no inflar conteos con dos monitores del mismo editor.
**Tanda C — Certificación O3:** usar el lector existente `src/radar_o3_full_window.py` y sus 7 FULL naturales posteriores al cutover; requerir 6/7 `STRICT_COMPLETE`, sin alterar `radar_definitivo.runs.status`. El corte histórico ahora aclara por qué el estado sigue rojo.

## Integridad de F5 entre repos
El sitio `poraca-lp` había aprobado F5 mediante una **simulación de dos fuentes por escena**, mientras este ejecutor preserva `F5_NOT_CHECKED` en `src/radar_f5_shadow_recovery.py`: una alternativa de investigación tras retirar una fuente en memoria no demuestra que el Radar recupere realmente el **mismo evento** al fallar el origen dominante. Adoptar el estado estricto pendiente hasta prueba operativa. El material histórico sigue siendo evidencia útil, pero no un PASS de resiliencia productiva.

**Coste de esta auditoría:** 0 ingestas, 0 ejecuciones FULL adicionales, 0 SQL de escritura, 0 cambios de programación, 0 despliegues de web. Solo 1 QA corta de código cuando corresponda.
