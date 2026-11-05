# Radar 2: paneo rotativo de Instagram — prueba del 05/11/2026

**Resultado: rotación y descubrimiento web funcionando en la prueba manual;
contenido propio de Instagram no demostrado; ejecución programada no certificada.**

Código integrado en main: `9fba86212eb0fa99ced2048fba2634336318e726` y su
corrección posterior de reanudación de leases. La misma tarea existente fue
actualizada; no se creó otro Radar, arquitectura, tarea, workflow o servicio.

## Qué se implementó

| Requisito | Evidencia y estado |
|---|---|
| Conservar padrón | 123 usuarios válidos exportados de `public.radar_lab_sources`; las otras tres referencias `research-*` permanecen fuera de Instagram, sin borrar nada |
| Rotar unos diez | Selección persistente en Neon, prioridad cultural dentro de cada vuelta, cooldown y lease; versión CAS impide sobrescrituras concurrentes |
| Descubrimiento público | Dos consultas por referente: índice de Instagram y red web; la búsqueda general deja de excluir Instagram |
| Límite de adquisición | No se solicita HTML de Instagram ni de sus espejos; se conserva solamente el extracto del índice si el buscador devuelve un enlace real de Instagram |
| Estado acumulado | Última revisión, intento, resultado por canal y próxima revisión; inicialización idempotente; mismo run reutiliza su lote y un lote completado no se repite |
| Persistencia cultural | Colector, intérprete, conciliador, escritor limitado y API existentes; evidencia original, clasificación, fechas, nulos y alias |
| Ejecutable programado | Integración preparada en la misma tarea; sigue bloqueado/no certificado por las dependencias ausentes en el último ejecutor real |

Estado guardado sin migraciones ni elevación de permisos, en la fila reservada
`radar2.runs / radar2-instagram-rotation-state-v1`. Su summary tiene
`type=instagram_rotation_control`, `status=control_state`, 123 cuentas y versión 3
al cierre de la prueba. Es una fila de control y **no una adquisición**.

## Prueba manual real

Run: `radar2-ig-manual-20261105T094500Z` (identificador lógico propio, fuera de las
ventanas ordinarias). Contexto: Work interactivo. Reclamo del lote 06:29 ART;
finalización de revisiones 06:36 ART. No se reclamó ni repitió un slot ordinario.

Referentes efectivamente consultados por buscador: `centrodearteunlp`,
`ciudaddegatos`, `escenario40`, `guajira.bar`, `intra.prod`, `lutitravelguide`,
`888casa`, `_rbcafe`, `asoc.mayo`, `astorbirra`.

| Medida | Resultado |
|---|---:|
| Cuentas seleccionadas y revisadas por buscador | 10 |
| Consultas lógicas del manifiesto final | 20 |
| Enlaces reales de instagram.com obtenidos | 0 |
| Perfiles de Instagram descargados | 0 |
| Publicaciones obtenidas mediante API Meta | 0 |
| Documentos externos adquiridos y persistidos en la muestra final | 12 |
| Observaciones persistidas, incluyendo repeticiones y documentos investigables | 18 |
| Propuestas culturales nuevas tras descontar inventarios anteriores y alias | 3 |

Se hicieron comprobaciones de cobertura de los buscadores; algunas búsquedas
con `site:instagram.com` y filtro de dominio devolvieron páginas de otros hosts.
El filtro final las descartó del canal Instagram. No son publicaciones leídas.
Las consultas, fechas y hashes de respuestas del manifiesto final están en
`radar2/evidence/instagram-rotation-20261105.json`. No se publican cuerpos
completos de las respuestas de los buscadores ni credenciales.

Las tres novedades son **web indirecta**, procedentes de Eleven Flow, con
`review_state=observado_agenda`, categoría Música y sede Ciudad de Gatos:

| Propuesta | Fecha y hora ART | ID |
|---|---|---|
| Cerounno, Vinyltracker, Juan 97 | 06/11/2026 20:00 | `0f438bc6610a4bd3fe23724756119e7563faa061c4d4db860b743f10aec6350f` |
| Mujer Cebra | 13/11/2026 20:00 | `8f7dcbc14fadb8d405509f5526d6bf81d64db18690bb80b8be04e1fb31a6b7b0` |
| Joaco Burgos | 13/12/2026 20:00 | `59684e30a84ddef6076b72e91c9cdea9c4d18702516e9ca10263481fb8b4fcab` |

Se comprobaron las tres mediante el conector autenticado de Vercel, contra
`https://poraca-lp-privado.vercel.app/api/radar2?id=ID`: HTTP 200, ID exacto,
título, fecha, hora, sede, fuente, clasificación y estado. No se admitieron al
canónico: continúan en la consulta privada de Radar 2.

Los Espíritus se descontó por estar en antecedentes; también se descontaron
Panter, Lolo Morales, Doble Par, Fábrica de chicas y otras observaciones ya
conocidas o conciliadas. El intérprete utiliza el performer explícito cuando una
fuente entrega como nombre genérico «Venta de tickets» y evita confundir claves
JSON o rutas de imágenes con personas o fuentes culturales.

## Continuidad y verificaciones

Los diez registros tienen revisión y próxima revisión, con cero enlaces propios
de Instagram. El preview leído desde el estado persistido prepara otros diez:
`aulavivafcnym.ok`, `baigon58.cerveza`, `barlaunion`, `barrio_meridianov`,
`blondie.cultural`, `bocanada.bar`, `bonodori_laplata`, `buenosairescultura`,
`c.f.josehernandez`, `cariniolibreria`.

Se verificó contra Neon que una actualización con versión vieja devuelve cero
filas y que reclamar nuevamente el mismo run reutiliza el lote. Pasaron tres
pruebas unitarias de rotación/cooldown/adquisición solo de extractos, y una prueba
Node de conservación de resultados indexados, aislamiento de fallo individual y
continuidad de fuentes web. La prueba del parser con un enlace Instagram fue
**sintética**: no incrementa el contador de resultados reales.

## Ejecutor programado: límite concreto

Tarea existente: `6ae17dc595d08191b5ec9a4ef0dcaa30`, Por Acá — Radar 2 cultural.
Conserva sus horarios y ventanas. Se actualizó su prompt en el lugar con carga
de los archivos, reclamo del lote, options.rotation, persistencia, readback y
finalización. Un fallo específico de Instagram no detiene el resto de fuentes.

La última corrida real registrada, ID del scheduler
`3526031e-8bd0-8324-98b3-f2be2c63dd6c`, slot `radar2-slot-20261105-05`,
correspondiente a las 05:07 ART, informó ausencia del servicio de búsqueda y del
puente para ejecutar Python. El scheduler la registra completed, mientras que
el run de Radar quedó blocked: son estados distintos.

Se pidió ejecutar la tarea existente ahora una sola vez. La plataforma respondió
`Ready to run in this conversation` con `inline_run`; no lanzó otro ejecutor.
El prompt devuelto se evaluó en esta conversación: al estar fuera de las
ventanas ordinarias, no se reclamó ni adquirió otro slot. Esto **no prueba ni
corrige** las dependencias de un worker programado. La API de actualización de
la tarea no ofrece campos para aprovisionar búsqueda o un runtime; nombrar esas
herramientas en el prompt no las instala. No se afirma operación automática.

Para cerrar esa aceptación hace falta una corrida en el ejecutor programado real
con búsqueda disponible, Python ejecutado, escritura limitada y lectura de los
IDs producidos en ese mismo contexto. No hay una ejecución nueva independiente
que permita certificarlo al cierre de esta intervención.

## API oficial de Meta

Se evaluó el adaptador existente `radar2/instagram.py`, Business Discovery con
Facebook Login. En este entorno faltan `META_IG_USER_ID`, `META_ACCESS_TOKEN` y
`META_GRAPH_VERSION`: las 19 identidades no ambiguas del archivo de referentes
retornaron `NOT_EXECUTED_MISSING_OFFICIAL_ACCESS`, y la identidad ambigua quedó
sin ejecutar. No se enviaron peticiones autenticadas ni se verificó elegibilidad
del padrón de 123.

La colección oficial de Meta en Postman documenta cuenta profesional, app,
token y vinculación de una página para el camino Facebook Login, y excluye
cuentas personales de consumo. Fuente consultada el 05/11:
https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api
La referencia directa de Business Discovery respondió 429 al consultarla;
los permisos y el nivel de acceso concretos deberán verificarse con la app y
versión reales antes de habilitar ese adaptador.

El acceso experimental por HTML del 04/11 permanece separado de la autorización
para producción. No se reutilizó como monitoreo ni se sustituyó por scraping de
espejos. Quedó funcionando y demostrado el paneo persistente de referentes y su
red web; todavía no la adquisición propia de Instagram ni la autonomía programada.
