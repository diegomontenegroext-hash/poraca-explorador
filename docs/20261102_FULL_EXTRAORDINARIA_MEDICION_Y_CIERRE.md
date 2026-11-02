# Por Acá — FULL extraordinaria del 2/11/2026, medición y cierre de iteración

**Corte:** 02/11/2026 11:18 ART. **Ámbito:** Neon operativo `frosty-union-52906378`, rama **`br-mute-recipe-b4odj2bl`** / `neondb`. No usar rama predeterminada como Por Acá. El control es sobre observaciones y pruebas ejecutadas, no una aprobación de publicación.

## 1. Ejecución extraordinaria, una sola
- Solicitud del usuario: ejecutar FULL para medir las mejoras, con mecanismo normal sin nueva tarea ni rama.
- [Commit disparador](https://github.com/diegomontenegroext-hash/poraca-explorador/commit/68a2347cbb3da0b303b77d4dbab3be4dd36e299b): `ops/radar-fallback-trigger.txt`, slot `bootstrap`, mode `full`; **no se modificó la programación de 05/13/21 ART**.
- [GitHub Actions run 41458818377](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41458818377): workflow **SUCCESS**. QA, ingesta a staging, pulso por rubro, lectura directa Neon, integridad L4, puertas ejecutivas y acta de cierre tuvieron steps SUCCESS.
- Neon: `definitivo-20261102T140653Z-1efe1c` inició **11:06:53 ART**, finalizó **11:12:49 ART**, `mode=full`, **status=partial**. La etiqueta `partial` es correcta y no se cambia manualmente: una fuente devolvió error HTTP 503. Workflow SUCCESS no implica FULL COMPLETE.
- Previo comparable: `definitivo-20261102T085408Z-cc1833`, 05:54 ART, `mode=full`, `status=complete`.

## 2. Comparativa reproducible
SQL versionada y probada: [comparación solo SELECT](../sql/20261102_full_impact_comparison_READ_ONLY.sql).

| Medida | FULL 05:54 | FULL 11:06 |
|---|---:|---:|
| Fuentes `fetch` con comprobación | 62 | 62 |
| Fuentes `fetch` con sesiones reportadas | 24 | 24 |
| Fuentes `fetch` con HTTP/extracción OK | 30 | 30 |
| Fuentes `index_only` | 32 | 31 |
| Fuentes `failed` | 0 | **1** |
| Detecciones reportadas (NO únicas) | 224 | 226 |
| `candidates_new` (candidatos técnicos del motor) | 19 | 6 |
| `listing_occurrences` nuevas, por `first_run_id` | 38 | **3** |
| `listing_occurrences` total en Neon al cierre | — | **519** |
| `listing_occurrences` futuras | — | **285** |
| Eventos canónicos totales | — | **144** |
| Salud global reportada | correcto | parcial |

Las 63 comprobaciones de la FULL anterior incluían un canal `discover_only` adicional (Luti); **no confundir 63 vs 62 con la pérdida de una fuente `fetch`**.

Las 3 nuevas `listing_occurrences` de la FULL extraordinaria son:
1. **Fábrica de chicas**, 29/11 20:00, Escenario 40, agenda secundaria Genda.
2. **Modelo vivo muerto**, 29/11 20:30, Coliseo Podestá, agenda secundaria Genda.
3. **Fernando Cabrera & Hugo Fattoruso**, 01/12 21:00, Casa Metro, URL primaria de Casa Metro.

Las tres están `observed_unverified`; ninguno es un evento aprobado por esta prueba. `candidates_new` y `listing_occurrences` son entidades técnicas diferentes, no deben forzarse a sumar igual.

**Conclusión de cobertura:** 24 fuentes con actividad, sin incremento probado todavía. La detección de 3 nuevas fichas de staging y la reobservación idempotente sí están demostradas. La siguiente FULL ordinaria deberá evaluar recuperación sin inferir que una fuente `index_only` carece de actividades en la ciudad.

## 3. Única falla real y recuperación controlada
- Fuente: `rd-web-2f6489bc`, Museo Pettoruti, URL `https://www.gba.gob.ar/museo_pettoruti/muestras`, circuito `arte_y_cultura`.
- FULL anterior: `index_only` con HTTP 200; FULL extraordinaria: `failed` con **HTTP 503 / HTTP_ERROR**. No se deshabilitó ni editó la fuente; falla posiblemente transitoria.
- Se integró **un único reintento universal acotado para HTTP 500/502/503/504** en el transporte existente `Budget.request()`, limitado por presupuesto, por host y por tiempo; nunca para 429, 403 o Instagram. [Código](https://github.com/diegomontenegroext-hash/poraca-explorador/commit/8647985954f0778c76b2772d4d3a4a63a8c2e097) y [tests](https://github.com/diegomontenegroext-hash/poraca-explorador/commit/9ccac97255fb1256fc4ca1ed375e28a3d155736b).
- Vercel Sandbox independiente sobre commit `9ccac97`: **367 tests ejecutados, 366 PASS, 1 SKIPPED, 0 FAIL**, exit code 0, incluidos 25 tests del motor definitivo.
- **Sonda HTTP real, solo lectura y sin Neon**, desde Vercel Sandbox con mismo `Budget.request()` y mismo URL institucional: **HTTP 200**, respuesta HTML 185.736 caracteres, **1 solicitud**, sin necesidad de reintento. Esto demuestra acceso recuperado en la sonda, no que una FULL reejecutada con el parche ya tenga PASS.
- **No se disparó una segunda FULL artificial**. El próximo chequeo ordinario certificará si se mantiene el 200 y si el reintento evita falsos cortes por fallas transitorias.

## 4. Cobertura cruzada; evitar sumar canales duplicados
El inventario tiene `rd-official-freezer-2026`, calendario oficial **`https://festival.freezer.com.ar/2026/programacion.ics`**, clasificado en `arte_y_cultura`, NO en `festival`. Neon tiene **24 `listing_occurrences` futuras** entre 05 y 17/11 extraídas de esa fuente y **1 coincidencia canónica por URL/título Freezer**. Por ello, un indicador `festival=0` por circuito no demuestra ausencia de festivales: **source.circuit es clasificación de la fuente, no taxonomía exhaustiva de sus eventos**. La programación original: https://festival.freezer.com.ar/2026/programacion/.

**Acción estratégica:** no inscribir nuevamente Freezer como fuente `festival` solo para cerrar un cero; primero conciliar inventario de fuentes con observaciones reales y originalidad/duplicación. Los seis circuitos con cero rendimiento en la medición de fuente siguen siendo señal de clasificación y recuperación, no seis inexistencias de actividades.

## 5. Integridad y semáforo después de FULL
- `public.radar_agenda_events`: **144 canónicos**, sin altas de esta prueba; `listing_occurrences`: **519**, de los cuales 285 futuros.
- Malena Muyala: **5 staging, 0 canónicos**; sigue pendiente el recibo editorial. No simular aceptación/visibilidad por haber confirmado el original.
- Puertas del SQL ejecutivo leídas después de la FULL: **5 PASS / 3 PARTIAL / 1 FAIL / 2 NOT_CHECKED**. `SOURCE_FETCH_HEALTH` pasó temporalmente a PARTIAL por el 503; además PARTIAL `COVERAGE_BY_CIRCUIT` y `STABILITY`; FAIL `LEAST_PRIVILEGE` por cuentas legacy; NOT_CHECKED `DIRECT_RADAR_AND_API_HTTP` (el SQL no hace HTTP) y `WEB_SSO_UX` (sin navegador SSO real). El HTTP API cuenta con evidencia externa anterior, separada del control SQL.
- La estabilidad 3/7 días depende de observaciones naturales; un ensayo ad hoc no adelanta un período completo.
- No se modificaron permisos Neon, eventos canónicos, recibos editoriales ni Deployment Protection.

## 6. Próximo cierre sin nuevos motores
1. En la siguiente ejecución ordinaria evaluar 62 fuentes, rendimiento real por circuito, `index_only`, 503 recuperado y apariciones nuevas, con [SQL comparativa](../sql/20261102_full_impact_comparison_READ_ONLY.sql) y reporte de rendimiento en el workflow actual.
2. Determinar independencia de fuentes **sobre eventos originales**, no por número de monitores; priorizar vinos/talleres/yoga y cobertura cruzada de festivales.
3. Completar **decisión editorial real** para una función testigo, sin `INSERT` directo para forzar un PASS; readback Neon→API→SSO tras recibo autorizado.
4. Cerrar roles legados únicamente mediante un procedimiento Neon administrativamente permitido. `poraca_explorador_writer` **posee** la base `poraca_explorador` y sus tablas; no borrar ni retirar sin migración de propiedad.
5. Ejecutar Chromium autenticado de producción sin quitar SSO y acreditar estabilidad 3/7 días con período real.

**Cierre de iteración:** FULL efectivamente ejecutada y medida, 503 identificado y acceso posterior 200, corrección transversal integrada y 367 tests PASS/SKIP, integridad sin pérdida, sin segundo Radar ni falso certificado global.
