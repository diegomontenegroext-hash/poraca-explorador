# Por Acá — cierre técnico de iteración, 02/11/2026
**Corte operativo:** posterior a la FULL de 05:54 ART y al commit `cc5a7117`. **Verificación:** conector GitHub, Neon SELECT sobre rama operativa explícita, Vercel autenticado y QA aislado con 352 tests. **No es certificado de estabilidad 3/7 ni de navegador SSO real.**

## 1. Resiliencia cultural implementada en el motor existente
Sin crear motor, rama adicional, cron ni modificar políticas de admisión:
- `src/radar_source_recovery.py` entrega `circuitResilience` con `fetchSources`, `reportedDatedYieldSources7d`, `fetchSourcesWithoutReportedDatedYield7d` y `sourceResilienceGate`.
- `discover_only` y `review` **no cuentan** como extracción productiva de funciones.
- Si un circuito aparece en un original futuro local investigado fuera de Radar pero **no tiene ninguna fuente fetch**, el informe lo marca con `futureOriginalResearchHint` y cero fuentes, sin inscribir fuente/evento ni afirmar cobertura.
- Un original futuro solo entra en esa cola si contiene URL HTTPS, fecha de la misma función, hora, sede y actor localizado en el área admitida. No extrapolar citas históricas ni páginas de otra jurisdicción.
- **Nunca** marca `resilienceCertified=true` solo porque haya dos canales: las sesiones pueden ser duplicadas, un agregador puede citar a otro y todavía falta evidencia independiente y admisión.
- Commits: [métrica inicial](https://github.com/diegomontenegroext-hash/poraca-explorador/commit/0d094826b378698bb566e8af95faa24c26a4a663), [semántica de original local y circuito sin fuente](https://github.com/diegomontenegroext-hash/poraca-explorador/commit/71331cfbbfd1e410bbd1ce59be3ee74d5c2797ba), [pruebas finales](https://github.com/diegomontenegroext-hash/poraca-explorador/commit/cc5a7117cbbb732ab5b6fc5e8b0cf1e916c933b2).

## 2. QA real, sin credenciales de producción
Vercel Sandbox `poraca-circuit-resilience-qa-20261102`, sesión `sbx_EOBpnTHBPEXVc8A2Q5C67WVxc9Bv`, repositorio público clonado en commit exacto `cc5a7117`.
- `python3 -m unittest discover -s tests -p 'test_radar_source_*.py'`: **27 PASS**.
- `python3 -m unittest discover -s tests -p 'test_radar_category_pulse.py'`: **9 PASS**.
- `python3 -m unittest discover -s tests -q`: **352 tests, OK (skipped=1), exit 0**. Un aviso `SyntaxWarning` de escape inválido en el test de descubrimiento preexistente **no** produjo fallo.
- La prueba no necesitó conexiones Neon ni datos privados, no hizo DML. Se apagó la sesión después del QA para liberar recursos.
- **NO** es QA browser prod: el sandbox carece de `vercel/vc`, Chromium, Playwright, agent-browser y tokens SSO/OIDC. El QA local Chromium anterior del sitio y el GET HTTP autenticado de Vercel permanecen como evidencias separadas, no equivalentes a navegador SSO autenticado en producción.

## 3. Métrica reproducible contra Neon operativa
Repositorio: [SQL solo SELECT para la última FULL](https://github.com/diegomontenegroext-hash/poraca-explorador/blob/main/sql/20261102_circuit_source_yield_last_full_READ_ONLY.sql). **Probado en** proyecto `frosty-union-52906378`, rama específica `br-mute-recipe-b4odj2bl` / `neondb`. No utilizar rama predeterminada de Bitácora.

Corte de `definitivo-20261102T085408Z-cc1833` (`full / complete`), 62 fuentes fetch, 30 `ok`, 32 `index_only`, 0 fallos; 1 semilla extra `discover_only`. Por sesiones realmente reportadas:
- **6/15 circuitos con 0 fuentes que extraigan sesiones:** `deportes_nauticos`, `festival`, `gastronomia`, `talleres`, `vinos`, `yoga`. Esto NO significa que la ciudad carezca de esas actividades; sólo evidencia un hueco de extracción de la FULL.
- **3/15 con 1 canal que reportó sesiones:** `ciencia`, `danza`, `literatura`. Son dependencias de fuente no necesariamente de organizador; no declarar redundancia.
- **6/15 con 2 o más canales con sesiones:** `arte_y_cultura`, `general`, `cine`, `teatro`, `musica`, `teatro_y_musica`. NO prueba diversidad independiente ni eventos únicos.
- En `talleres` hubo 1 HTTP/fetch OK, pero **0 sesiones reportadas**. Esto ejemplifica por qué rendimiento real ≠ transporte exitoso.
- Las observaciones crudas pueden representar la misma función varias veces: no sumar `reported_sightings` como eventos confirmados.

## 4. Verificaciones públicas del circuito vinos / falsos positivos territoriales
- **Verdadero original local:** [Feria Catar V](https://www.passline.com/eventos/feria-catar-v-edicion), 27/11/2026 19–23, Paseo Mitre, 485 y 138, Gorina; organizador indicado por ticketera `Asociacion Civil de Sommelier de Buenos Aires`. Antes de cualquier inscripción: 0 coincidencias en staging / 0 canónicos. Sigue pista externa respaldada; no evento generado por Radar.
- [La Tapería — Noche de las Vinotecas 13/11](https://lataperia.com.ar/eventos/) aparece en búsquedas amplias, pero [su sitio original la ubica en Güemes, Córdoba, Belgrano 647](https://lataperia.com.ar/about-us/). **Excluir del circuito territorial Por Acá**. No sumar como segundo canal de La Plata por homonimia/tema.
- Un directorio de Eventbrite rotulado «Vinos en La Plata» mezcla eventos de **CABA/Monserrat**; verificar dirección original de cada anuncio (p. ej. [Licorería Paradiso, México 802, Monserrat](https://www.eventbrite.com.ar/e/vinos-al-paso-edicion-especial-noche-de-las-vinotecas-tickets-2003852967167)). No inferir geolocalización desde la página de resultados o etiquetas de buscador.
- `Feria Catar` no demuestra que los antiguos colaboradores de Casa Dionisio sean organizadores actuales ni que ACSBA comparta organización con Dionisio.

## 5. Puertas pendientes, sin falso cierre
| Puerta | Estado al 02/11 | Evidencia exigida para cerrar |
|---|---|---|
| Cobertura por circuito | PARTIAL | FULL ordinaria con el código nuevo; 1 original futuro nativo extraído de fuente nueva y luego verificación de dos canales realmente independientes para vinos; medir 32 index_only por propósito, sin simular productividad |
| Admisión fresca | PENDIENTE | Malena 21/11: 5 lecturas staging/0 canon; recibo de revisión separado + alta mediante mecanismo formal + readback Neon/API/UI con negativos |
| Privilegios legados | FAIL | Dos logins con `neon_superuser`; 0 objetos de propiedad y 0 sesiones visibles solo son preflight, NO prueba de inexistencia de referencias en secretos; identificar consumidores y retirar uno por vez mediante administración autorizada y rollback |
| UX SSO producción | NOT_CHECKED | Chromium real con autenticación adecuada y cuatro perfiles; no quitar Deployment Protection |
| Estabilidad 3/7 | PARTIAL | Health-v2 sin brechas: earliest 05/11 y 09/11 si saludables, sin corridas falsas |
| HTTP API/SSO GET | PASS externo previo | Evidencia autenticada anterior, distinta del gate SQL que no ejecuta HTTP |
| Integridad canónica | PASS con evidencia previa | 133 IDs supervivientes, 0 huérfanos y 0 faltantes de recibos, no reinterpretar alarma heredada V1 como defecto nuevo |

**Decisión:** se cierra **implementación y QA de resiliencia por circuito**, NO el certificado global punta a punta. Las tres trabas restantes activas (fuentes originales/aceptación, privilegios históricos, navegador SSO) y el tiempo 3/7 siguen abiertas. No ejecutar DML editorial, revocación administrativa, FULL de compensación, alta automática de fuente ni publicación de un evento para forzar un verde.
