# Fuentes culturales compuestas — cierre de intervención

**Implementado y verificado en producción. NO GO para certificar la capacidad integral con los umbrales 95%/90%/95%.** La pérdida principal de artículos enteros y curadurías quedó corregida en los casos comprobados. Las dos subactividades narrativas conocidas también quedaron resueltas con `compound-v1.1`; falta una evaluación editorial independiente suficiente. El motor privado conserva su GO condicionado previo; esto no concede certificación autónoma.

Código de aceptación general: `f7b51553d20e5c3ba6e6b16b87a869a080d39009`. Código final de límites/caché/consulta: **`2c346ca96795fb853afb671f9e2cec848cdf331c`**, `main`. Intérpretes actuales `compound-v1.1` y `caption-v2.3`; la corrección final se detalla al cierre de esta acta. [Issue #20](https://github.com/diegomontenegroext-hash/poraca-explorador/issues/20) permanece abierto; no se creó otro backlog.

## A. Implementación

- Se reconocen carteleras con horarios, agendas por filas y recomendaciones por encabezados/días. Se interpretan listas, días compartidos, intervalos y fechas relativas desde publicación ART. Cada actividad tiene título y sede locales; los desconocidos se conservan como tales.
- Se separan documento, evento, funciones, programa, lugar y recomendación permanente. No se asigna el primer título o lugar de una publicación a todas sus actividades. Un programa multisede conserva lugares distintos y las ocurrencias sin resolver, sin inventarlas.
- Una curaduría produce `recommended_by`; no se transforma en organizador. Las notas periodísticas son evidencia secundaria. El rol de organizador requiere crédito explícito. Hay evidencia textual y spans originales; no hubo transcripción de videos.
- Los adaptadores estructurados mantienen precedencia. Una cartelera de bandas de un mismo show no se divide automáticamente en un evento por artista. Los formatos desconocidos/ambiguos no se fuerzan para mejorar una métrica.
- El descubrimiento periodístico prioriza agendas recientes por sus enlaces, sin permalink fijo. Se incorpora cadencia según tipo/productividad dentro del workflow existente. FULL mantiene siete días de Genda; incremental consulta uno. Puede añadirse una consulta curatorial productiva en incrementales de miércoles a viernes, sin desplazar la rotación equitativa.
- El hash y la versión del intérprete controlan reutilización; la marca documental también admite resultados vacíos sin fabricar propuestas. Se preservan bloques y datos estructurados de originales nuevos para futuros replays.

## B. Corpus y calidad

Se conservaron seis originales testigo de desarrollo, una reserva de cinco documentos con etiquetas parciales y sus primeras predicciones, revisiones posteriores y regresiones de formatos ya resueltos. Los originales completos siguen en Neon/versiones. Scripts reproducibles: `evaluate_compound.py`, `compound_replay.py`; pruebas `test_radar2_compound.py` y existentes.

**La anotación fue del agente, sin validación humana independiente.** La reserva usa formatos conocidos durante el desarrollo y contiene etiquetas completas de conteo, pero solo una selección de campos. No se presenta como benchmark independiente suficiente ni se calcula una precisión integral con campos no etiquetados.

| Control real | Resultado final | Límite |
|---|---:|---|
| Agenda 0221 del 31/10 reservada | 28 candidatos fechados, 28 esperados | Cuatro muestras de título/fecha/hora/sede correctas; no todas sus identidades fueron auditadas. |
| Agenda El Día del 01/11 reservada | **23 de 23 actividades esperadas** | Cierre coral y libro individualizados; conteo del agente, sin validación humana independiente. |
| Caption curatorial reservado del 14/10 | 11 candidatos, diez fechados y uno sin fecha | La primera pasada produjo cuatro; tras corregir segmentación por líneas dejó de ser reserva independiente. |
| Dos reseñas permanentes | Cero eventos fechados; dos recomendaciones de lugares | Una es de Castelli, marcada fuera del ámbito local; no se inventó un evento platense. |
| Campos de muestra en dos agendas reservadas | 10/10 coincidencias de título/fecha/hora/sede | Muestra parcial; no prueba 95% integral de campos, organizadores o actores. |

Puertas: **recuperación integral: NO DEMOSTRADA fuera de los casos revisados; precisión de candidatos ≥90%: NO CERTIFICADA; exactitud crítica ≥95%: NO CERTIFICADA**. Tampoco se ha certificado cero fusiones semánticas incorrectas en todo el corpus. Los desconocidos y las marcas de ambigüedad no se convierten en aciertos inventados.

[Reserva y primera evaluación](evidence/compound-reserved-results-20261107.json) · [revisión posterior](evidence/compound-post-review-20261107.json) · [originales testigo](evidence/compound-regression-originals-20261107.json).

## C. Recuperación y comparación antes/después

La recuperación selectiva consultó **11 originales guardados, sin adquisición externa**, escribió y releyó 318 propuestas. La repetición conservó los IDs y agregó cero nodos/relaciones; retiró cero interpretaciones adicionales. Se conservaron 78 alias con evidencia; no son 318 eventos nuevos ni necesariamente futuros.

| Testigo | Antes de esta misión | Después de recuperación |
|---|---|---|
| El Día, 06/11 | Una propuesta genérica, cero fechadas | **88 actividades/funciones**, 86 con fecha/hora/sede. |
| 0221, 05/11 | Una genérica, cero fechadas | **42 actividades**, 38 con los tres campos. |
| 0221, 06/11 | Una genérica, cero fechadas | **33 actividades**, 29 con los tres campos. |
| Luti, reel DfVEIVTSTGu | Una propuesta fechada con título general | **16 recomendaciones/ocurrencias**, títulos locales y sedes explícitas cuando existen. |
| Luti, reel DfDGyw_SkDA | Una genérica sin fecha | **13 unidades**; menú y charla separados sin atribuirles un mismo horario. |
| Luti, reel DeXYqWISZod | Nueve fechas con interpretación insuficiente | **Diez ocurrencias**, incluidas dos fechas explícitas y un intervalo sin expansión diaria; sedes locales y programa multisede sin sede única supuesta. |
| Guajira, programa horario | Diez actividades ya resueltas | Diez, con los mismos títulos/fechas/horarios/sedes. |
| Cine, programa de tres películas | Tres actividades ya resueltas | Tres, con los mismos campos. |
| Reunión de padres | Tres funciones ya resueltas | Tres, sin regresión de campos. |

[Recuperación y matriz antes/después](evidence/compound-recovery-20261107.json) · [regresiones de formatos](evidence/compound-specialized-regression-20261107.json).

## D. Matriz de cobertura persistida

Corte después de FULL/incremental: intérprete `compound-v1`, observaciones activas antes de la conciliación visual. Incluye históricas. Los alias se conservan; no se suman como eventos culturales únicos.

| Fuente / formatos | Documentos | Propuestas | Actividades fechadas | Fecha/hora/sede | Ambiguas/incompletas | Coincidencias entre fuentes | Repeticiones del mismo medio |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0221 / agenda por filas | 4 | 148 | 148 | 132 | 16 | 8 | 48 |
| El Día / cartelera | 4 | 230 | 230 | 225 | 5 | 44 | 55 |
| Instagram / curadurías y recomendaciones | 8 | 69 | 60 | 0 | 69 | 0 | 0 |

Las 69 propuestas de Instagram incluyen ocho recomendaciones permanentes y una recomendación sin fecha, además de las actividades fechadas. No se les atribuyeron horarios ausentes del caption. Las 52 coincidencias entre fuentes son **candidatas de conciliación**, no 52 corroboraciones primarias certificadas ni aprobaciones. Los descartes de bloques no tienen todavía un contador semántico completo; no se inventó un cero. Las exclusiones de fuentes/enlaces y los errores técnicos están en los recibos de corrida.

[Datos de matriz](evidence/compound-source-coverage-20261107.json).

## E. Ejecuciones reales, persistencia e idempotencia

[Actions 42332669232 SUCCESS](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42332669232): recuperación, repetición, FULL e incremental en el workflow existente.

| Ejecución | Documentos escritos/releídos | Propuestas procesadas/releídas | Consultas Meta | Publicaciones oficiales nuevas |
|---|---:|---:|---:|---:|
| FULL | 641 | 1073 | 11 | 84 |
| Incremental inicial | 28 | 95 | 1 | 12 |
| Incremental final acotada | 10 | 35 | 0 | 0 |

La FULL tuvo siete errores de fuente y la incremental inicial cero; SUCCESS no los oculta. La segunda consulta Meta fue únicamente a `teatrolanonna_oficial`, la cuenta elegible recién admitida; no se afirmaron diez consultas. La recuperación no volvió a descargar los originales.

[Actions 42333406637 SUCCESS](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42333406637) verificó el código final: **una página de Genda, cero consultas Meta, cero errores de fuente**. Se procesaron tres captions conservados para registrar el nuevo control documental; no fueron nuevas descargas. El caché posterior se probó localmente, no durante días naturales.

La primera aceptación [42332441662](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42332441662) falló antes de adquisición/persistencia por tratar evidencia textual entrante como JSON. Se reprodujo y corrigió antes de repetir; no se omitió este fallo del historial.

Inventario final: **974 documentos, 1054 versiones documentales, 1779 propuestas, 6468 versiones de propuestas**. Cero originales actuales sin versión, cero referencias colgantes y cero autoaprobaciones. No se borró ni reinició Neon.

[Corridas](evidence/compound-runs-20261107.json) · [incremental final](evidence/compound-final-incremental-20261107.json) · [integridad final](evidence/compound-integrity-final-20261107.json).

## F. API, compatibilidad y regresiones

API privada HTTP 200 comprobada para recomendación curatorial, noticia conciliada, programa multisede y relación `recommended_by`. La consulta de relaciones inicialmente dio 503 y el log informó QUERY_FAILURE. Materializar la vista de ocurrencias una vez por consulta eliminó el recálculo por arista y restituyó HTTP 200. En el clon existente, **3621 registros conservan exactamente el mismo digest antes/después**. No cambió el contrato, no hubo tabla/servicio/cron nuevo ni permisos adicionales.

Producción existente `dpl_C5JjCbBCtHXZYfaRfFgGNabn4piG` READY; SSO all conservado. No hizo falta reconstruir o desplegar la web. El 503 fue una falla de consulta, no prueba de despliegue caído ni motivo para quitar protección.

Regresión de ledger: **89 registros previos de Genda y ocho de TeatroCerca**, cero IDs perdidos y cero cambios de título/fecha/hora/sede. Eso prueba conservación de esa muestra; no certifica cobertura de toda la cartelera. Los extractores estructurados mantuvieron precedencia. Alternativa Teatral sigue teniendo limitaciones de listado dinámico, registradas explícitamente. **529 pruebas locales, una omitida**; no equivalen a precisión editorial.

[API y error observado](evidence/compound-api-20261107.json) · [relación corregida](evidence/compound-relationship-api-fixed-20261107.json) · [equivalencia de vista](evidence/compound-view-equivalence-20261107.json) · [regresión de ledger](evidence/compound-specialized-ledger-regression-20261107.json).

## G. Estado final y cierre

Quedan funcionando la desagregación por estructura, atribución local, recomendaciones sin evento ficticio, fechas ancladas a publicación, distinción curador/organizador, conciliación con procedencia, recuperación versionada, reutilización documental y consulta privada. Los tres horarios, roles restringidos, rotación oficial, archivo y SSO se conservan.

**El issue #20 permanece abierto** por dos obligaciones de aceptación: evaluación suficientemente independiente y completa de recuperación/precisión/campos/roles; observación natural de cadencia y rendimiento. Las sedes y títulos cuya frontera no está clara siguen pendientes de revisión; las coincidencias no se autoaprueban ni crean circuitos culturales por coaparición. La cadencia curatorial adicional está implementada, pero el calendario de esta prueba no ejerció la ventana miércoles-viernes.

No hay otra arquitectura ni otro backlog. La mejora está implementada y demostrada; la certificación integral no se simula.


## Acta final de terminación — compound-v1.1, 07/11/2026

**GO condicionado para uso privado con revisión editorial. NO GO para una certificación integral o credenciales totalmente autónomas.** Se terminó la corrección interna concreta pendiente de esta ampliación. No se afirma resolver toda construcción narrativa posible: los formatos no reconocidos y los campos ambiguos conservan revisión pendiente.

1. **Defectos corregidos:** además de la segmentación y atribución local anteriores, se extraen anuncios futuros internos explícitos con reloj o secuencia narrativa. Se conserva el programa principal. No se copian sus horarios a la presentación posterior ni se convierten bandas, descripciones o relatos pasados en eventos adicionales.
2. **Antes/después:** El Día del 01/11 pasó de 21 a **23 actividades**. El cierre coral queda el 01/11 a las **17:45**; `Versos de mi pago`, el mismo día, **sin horario conocido**. La sede contextual está marcada como tal; `escalinatas del museo` se conserva como sububicación. Las diez muestras previamente etiquetadas de dos agendas siguen coincidiendo. Esta reserva ya intervino en desarrollo y no es evaluación independiente.
3. **Identidades y relaciones:** cada subactividad conserva `parent_program_id`, relación `part_of_program` observada, cita exacta y spans; los lugares existentes se reutilizan con procedencia del programa. No se fusionaron identidades dudosas ni se afirmó corroboración humana. El vínculo al programa está dentro de `evidence`, compatible con v1; no se presenta como nuevo recurso de aristas.
4. **Descubrimiento genuino:** el documento original identifica un cierre coral específico en el Museo de Ciencias Naturales y una presentación de libro dentro de la premiación del certamen. Se consultan desde Neon y API como candidatos históricos relacionados con sus programas. No son próximos eventos útiles ni un circuito cultural inventado; el enriquecimiento relacional anterior permanece documentado en las evidencias de esta acta.
5. **Persistencia/API:** 23 propuestas escritas y releídas por corrida selectiva; las dos nuevas tienen respuesta **200** en la API protegida. Inventario: **974 originales / 1.054 versiones**, **1.781 propuestas / 6.540 versiones** al corte. Cero originales sin versión, padres de programa colgantes o autoaprobaciones. La repetición no añadió nodos ni relaciones. Las versiones de propuestas aumentan por trazabilidad de cada ejecución; no equivalen a eventos nuevos.
6. **Tres corridas:** horarios y rotación existentes conservados. FULL/incrementales técnicas reales ya pasaron las ejecuciones enlazadas arriba. Esta corrección usó **un original preservado y cero adquisiciones**, sin otra FULL ni Actions adicional. Sigue pendiente la observación de varios días de cron naturales y de la cadencia curatorial.
7. **Meta:** continúa Business Discovery oficial. Según la introspección documentada, token hasta **05/01/2027 19:08:08 ART**, acceso a datos hasta **04/02/2027 19:39:52 ART**; alertas preventivas y renovación humana. Esta intervención no renovó ni volvió a consultar la credencial. No se declara autonomía de credenciales.
8. **Límites:** faltan etiquetas y validación editorial humana independiente suficientes para demostrar precisión de ocurrencias ≥95% y recuperación ≥90%, con evaluación separada de campos y roles. Los umbrales adicionales anteriores del issue no sustituyen estas metas del mandato. El contador de descartes y la cobertura semántica total no se certifican. Continúan las limitaciones de captions sin video y de algunas fuentes dinámicas.
9. **Versión/pruebas:** `compound-v1.1`, compatible con `caption-v2.3` y contrato v1. **533 pruebas técnicas ejecutadas, una omitida**, más evaluación de originales, integridad, readback y API. Despliegue API existente conservado; no se requirió reconstrucción ni cambiar SSO. Código de esta corrección en el commit que incorpora esta acta a `main`.
10. **Decisión:** GO condicionado para descubrimiento privado y candidatos sujetos a revisión; NO GO para certificación integral 10/10. Se cierra la omisión narrativa conocida; el [backlog vigente #20](https://github.com/diegomontenegroext-hash/poraca-explorador/issues/20) conserva solamente obligaciones no demostradas, incluyendo ambigüedades editoriales y continuidad natural.

**Interrupción real y recuperación:** el primer intento guardó propuestas y se interrumpió en memoria cultural por HTTP proxy 403. Quedó registrado como `recovered_after_interruption`. Se completó mediante el conector autenticado; la primera lectura de baseline del conector estaba limitada a 100 filas y se corrigió recuperando el conjunto completo mediante agregación. La corrida final leyó el baseline completo, concilió tres alias, releyó 23 propuestas y agregó cero nodos/relaciones. No se presenta el intento parcial como aceptación correcta.

Evidencias finales: [evaluación](evidence/narrative-evaluation-20261107.json), [recuperación y repetición](evidence/narrative-recovery-20261107.json), [integridad](evidence/narrative-integrity-20261107.json), [API privada](evidence/narrative-api-20261107.json). No contienen credenciales ni enlaces temporales de acceso.
