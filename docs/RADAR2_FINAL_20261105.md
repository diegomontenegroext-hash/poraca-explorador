# Por Acá — cierre verificable de la misión final de Radar 2

Fecha local: jueves 05/11/2026 ART. Ejecuciones UTC: 06/11/2026.

**Decisión: GO PARCIAL.** La cadena ejecutada en GitHub → Neon → API privada está acreditada. Se integraron la rotación del padrón, exploración autónoma por enlaces y memoria cultural con evidencia. Instagram produjo cero publicaciones; tampoco se observó todavía el primer disparo natural del cron actualizado. No se declara inteligencia cultural universal ni adquisición de Instagram certificada.

## Código y ejecuciones

| Commit de código | Cambio | Ejecución real |
|---|---|---|
| `ebf058be64f1cc0c01db9b8e56cbdb648607d3f5` | Integración diaria, frontera de fuentes, memoria y dos lotes persistentes | [42145502319](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42145502319), SUCCESS; una adquisición diaria y un segundo lote acotado |
| `eeace52d592400d53f28ec576e386be1d8459910` | Fecha/horario de programas rotulados, créditos explícitos y archivo de documentos irrelevantes | [42146038206](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42146038206), SUCCESS; seis páginas de frontera, sin FULL ni Instagram |
| `2074b0cd5a0839446954f5d6f7adab3fa847dee2` | Conciliación del anuncio original con Genda, preservación de créditos y visibilidad en API existente | [42146423167](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42146423167), SUCCESS; cinco documentos, sin FULL ni Instagram |
| `a08ca0ccd604eb3e63c58ad8dca74b43928ca366` | Filtro cultural del propio enlace y referencias a identidades del staging existente | [42146682368](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42146682368), SUCCESS; cinco documentos, sin FULL ni Instagram |
| `fc45232861abddcbb187a9c8bddb62a080605be9` | Organizador verificado visible en API y conservado tras releer agenda | [42146830199](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42146830199), SUCCESS; seis documentos, sin FULL ni Instagram |

El commit de cierre añade esta acta, README vigente, evidencia JSON y una corrección conservadora del criterio de monitoreo: dos lecturas el mismo día no certifican continuidad. Esa última condición fue verificada localmente; la siguiente corrida diaria es su primera oportunidad de uso natural. No se atribuye una ejecución pasada a código posterior.

Pruebas: 483 en la suite completa, 482 PASS y una omitida. Las trece pruebas específicas cubren límites de acceso, atribución de perfil, equidad ante bloqueo, fechas/roles, deduplicación y conservación de créditos. CI del último código funcional: [42146830176](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42146830176), SUCCESS.

## Instagram: dos capacidades distintas

Padrón leído desde Neon: **123 cuentas**, sin borrados. Dos lotes guardados en `radar2-instagram-rotation-state-v1`, ambos `completed`, diez resultados cada uno y **cero cuentas repetidas**:

| Lote | Cuentas |
|---|---|
| `radar2-ghpilot-42145502319` | aulavivafcnym.ok, baigon58.cerveza, barlaunion, barrio_meridianov, blondie.cultural, bocanada.bar, bonodori_laplata, buenosairescultura, c.f.josehernandez, cariniolibreria |
| `radar2-ghpilot-42145502319-batch2` | casa.curutchet, casa.mutar, casa_unclan, casadeculturavillaelisa, casametrolp, casapulsarlaplata, casasesentaydos, casasuizalp, casatomadawinehouse, cervezabarfuss |

| Medida real en GitHub | Resultado |
|---|---:|
| Cuentas cuya condición de acceso se comprobó | 20 |
| Peticiones HTTP efectivas a perfiles | 0 |
| Perfiles accesibles acreditados | 0 |
| Publicaciones recuperadas | 0 |
| Propuestas nuevas procedentes de publicaciones de Instagram | 0 |
| Restricciones registradas por cuenta | 20 |
| Lotes diferentes con estado persistido | 2 |

El endpoint público de [robots de Instagram](https://www.instagram.com/robots.txt) respondió HTTP 200 y exige permiso escrito de Instagram para recolección automatizada. Huella SHA256: `3a62d0ddf2d87aa7cef3d1b7facf0bc49c10f7f4580755c0230fd2f89a679da5`. GitHub conservó URL, fecha, condición, aviso y huella en cada resultado. La restricción se comprobó antes de solicitar perfiles: no se fingieron veinte descargas ni veinte revisiones exitosas. Se avanzó la rotación mediante contador de intentos, manteniendo separados revisión exitosa y publicaciones.

El parser del método histórico quedó acotado a identidad explícita y captions y fue probado con fixture. **No fue posible reproducir su extracción en vivo respetando la restricción vigente.** Los enlaces a publicaciones siguen sujetos a esa misma condición; no se abrió una excepción por estar enlazados desde otra web.

Business Discovery devolvió `NOT_EXECUTED_MISSING_OFFICIAL_ACCESS` en las veinte cuentas: faltan app/cuenta/token/versión reales. No se enviaron peticiones autenticadas a Meta ni se verificó la elegibilidad del padrón. Las referencias de acceso oficiales son las del adaptador previo; no se afirma haber aprobado permisos o habilitado la API.

La búsqueda pública RSS de Bing también devolvió restricción de robots: 22 consultas lógicas entre ambos lotes, ninguna búsqueda productiva. Se almacenó el resultado negativo. La búsqueda exclusiva de Work no se convirtió ficticiamente en dependencia de GitHub. **Rotación PASS; adquisición de publicaciones BLOCKED.**

## Descubrimiento de fuentes y aprendizaje real

El enlace de una nota de 0221 llevó al sitio **lumenartis.org**, que no estaba precargado en Radar 2. No se entregó al ejecutor una URL humana de ese evento. Lumen Artis ya era un espacio conocido de Por Acá: lo nuevo fue descubrir y usar su canal como fuente del Radar, no inventar un espacio nuevo.

Fuente adquirida: [programa de Achmed](https://lumenartis.org/?post_type=funcion&p=2904). El programa informa sábado 7 de noviembre, 20:00. El intérprete verifica el día de la semana e identifica explícitamente que 2026 se infiere de la programación actual; no confunde el estreno cinematográfico de 1926 con la fecha de la función.

De esa fuente se registraron **Videodromo y seis músicos**: Nacho Stoppani, Sebastián Piatti, Lucas Muñoz, Tomás Szelagowski, Rob Astami y Rodrigo Runco. Los siete nombres no existían como créditos estructurados previos de Radar; una consulta de nombres exactos tampoco encontró coincidencias en `public.poraca_knowledge_entities`. Eso no resuelve posibles alias externos: quedan como identidades de adquisición pendientes de revisión editorial.

La fuente añade siete vínculos nuevos al evento ya conocido: `organized_by` para Videodromo y seis `features` para los músicos. Se unificó la variante «Teatro de Cámara de City Bell» con la sede que Genda denomina «Teatro de Cámara City Bell». La memoria final tiene **57 nodos activos y 112 relaciones activas**. Las otras 50 identidades y 105 relaciones provienen de estructurar evidencia preexistente: **no son nuevos descubrimientos**. Los alias y relaciones sustituidas conservan su historial.

Se conservó además como candidata la cartelera pública de próximos eventos de Lumen, con revisión futura persistida. También se descubrieron cuatro páginas de entradas en `publico.alternativateatral.com`, mediante enlaces de TeatroCerca. Permanecen documentos investigables cuando la respuesta pública no aporta la fecha. No son cuatro funciones nuevas certificadas. El subdominio es una nueva ruta operativa de una plataforma ya conocida, no una organización desconocida.

La frontera persiste candidatos, origen del enlace, primera detección, revisión, causas de fallo, próxima revisión y productividad. Lumen tiene extracción productiva repetida en dos pruebas controladas del mismo día. **Monitoreo sostenido no certificado**; `monitoring_certified=false`. No se promueve el resto de los candidatos por haber encontrado un enlace.

## Balance depurado de datos

Desde `2026-11-06T01:41:32Z`, confirmado con SELECT sobre Neon:

| Dato | Cantidad e interpretación |
|---|---|
| Nuevas URL documentales guardadas | 50; incluyen documentos investigables y descartes auditables |
| Nuevos IDs de observación | 12; no equivalen a doce eventos |
| Nuevos documentos culturales únicos activos | **6**, todos investigables |
| Nuevos eventos únicos | **0** después de conciliación |
| Evento conocido enriquecido | **1**, Achmed, con siete protagonistas nuevos para la memoria |
| Documentos irrelevantes archivados | 4: clasificados, fúnebres y dos enlaces para compartir |
| Documento sin interpretar sustituido | 1, precursor de la propuesta fechada de Lumen |
| Alias de evento conservado | 1, original de Lumen conciliado con Genda |
| Promociones editoriales/canónicas | **0** |

Seis documentos activos: ¡ACTÚEN!, Criminal, Escrito en la piel, La fiaca, la cartelera de próximos eventos de Lumen Artis y la nota «Una obra llega a La Plata para explorar la maternidad, el deseo y las formas de amar». Son nuevas evidencias para investigar; no se afirma que sus actividades fueran desconocidas en todo el sistema.

La identidad se contrasta también contra `radar_definitivo.entities` con el lector ya autorizado del escritor limitado; una coincidencia de nombre solo genera una referencia pendiente de revisión, nunca una fusión canónica.

La primera medición contó descartes aún no filtrados. Las correcciones los archivaron sin borrarlos y eliminaron el falso evento adicional. El balance final precedente sustituye esas cifras brutas, conservadas en cada run como historia de la prueba.

## Cadena privada comprobada

El escritor de GitHub fue `poraca_radar_limited_prod`, proyecto `frosty-union-52906378`, rama `br-mute-recipe-b4odj2bl`. Cada ejecución releyó sus propios documentos, propuestas y estado `completed` desde Neon. No se concedió acceso a tablas canónicas ni se cambió su estado editorial.

El conector autenticado de Vercel verificó a las **22:56:34 ART**:

- [API del evento conciliado](https://poraca-lp-privado.vercel.app/api/radar2?id=703b02b9cf6b6a77b2f3372e6437df3bba67562dbf894607796057753ea4f223): **HTTP 200, count=1**.
- ID `703b02b9cf6b6a77b2f3372e6437df3bba67562dbf894607796057753ea4f223`, fecha `2026-11-07`, hora `20:00`, sede y ocho entidades devueltas.
- Las entidades incluyen los siete créditos nuevos, IDs de nodo y relaciones al mismo evento, con la URL de Lumen como evidencia.
- `publication_approved=false`, `Cache-Control: private, no-store`, `X-Robots-Tag: noindex, nofollow, noarchive`.

La API existente no necesitó redeploy. Vercel se consultó sin teamId/slug opcionales; producción estaba READY y SSO `all` activo. No se desactivó protección. La evidencia resumida está en `radar2/evidence/final-certification-20261105.json` y en `summary.final_certification` del último run de Neon. La actualización final de metadatos también se hizo con el rol limitado verificado.

## Lo operativo y lo que no quedó acreditado

La siguiente corrida diaria está preparada para **viernes 06/11/2026, 05:27 ART**: adquisición existente, un lote de diez cuentas, condiciones de acceso verificadas, exploración de doce páginas como máximo, interpretación, conciliación, memoria, escritura y readback. Mismo workflow, mismo cron, mismas credenciales. Las opciones de los disparos de prueba no cambian el comportamiento de `schedule`.

No se acredita el disparo natural antes de que ocurra. Tampoco continuidad de varios días, cobertura completa del ecosistema o adquisición efectiva de Instagram. La exploración autónoma operativa es por enlaces; la búsqueda general independiente continúa bloqueada por las condiciones del proveedor público probado y no hay una API de búsqueda configurada. El grafo es memoria de adquisición dentro de Radar 2; las tablas públicas de conocimiento y la admisión editorial no fueron reemplazadas ni pobladas por fuera de su contrato.

**GO PARCIAL:** continuar con el motor web integrado y su memoria basada en evidencia. **NO GO para afirmar que Instagram es una fuente operativa o que la autonomía diaria sostenida ya está certificada.** Este cierre termina la intervención funcional realizada; no convierte los límites externos ni la evidencia pendiente en éxitos.
