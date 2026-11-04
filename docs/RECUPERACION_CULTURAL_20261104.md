# Recuperación de descubrimiento cultural · 04/11/2026

La mejora está implementada, ensayada sobre información real y reflejada en Neon/API privada. No prueba cobertura suficiente de toda la ciudad ni autonomía sostenida. IICS 1.0 histórico permanece **5,8/10**.

## Causas demostradas y corrección

- **0221:** no tenía extractor de listas editoriales; el dominio caía en JSON-LD Event únicamente, aunque sus agendas son NewsArticle con encabezados y listas. Además el orden alfabético de enlaces podía consumir el presupuesto con notas anteriores. Ahora se extraen fecha explícita, hora y sede de cada tarjeta bajo su encabezado; se conserva siempre evidencia secundaria. Se priorizan dos agendas y se rota el resto.
- **El Día:** se prohibían los artículos que no coincidían con slugs de agenda recientes. Se recuperan notas culturales realmente enlazadas y su extracto público; no se intenta superar muros de pago. Las notas no se convierten en sesiones por tener fecha de publicación.
- **Luti:** el buzón solo contenía otro reel y vencía hoy. El exacto aportado no estaba en la cola. El separador exigía día y cuenta en la misma línea y perdía encabezados separados y bloques con fechas. Se agregan los dos permalinks al buzón existente, se conservan secciones literales y cuentas y se rechaza HTML sin caption legible como cobertura.
- **Identidades:** una página original de un espacio podía quedar index_only por carecer de una función futura. Se conserva su descripción como propuesta de identidad, sin afirmar programación vigente. No se infieren horarios de clases.
- **Muerde:** ticket WeVix original enlazado por el organizador carece de JSON-LD Event. Adaptador acotado al detalle con título, año, hora y sede visibles; no interpreta la URL como fecha.
- Se agrega un resultado cultural separado del HTTP en source_outcomes de las corridas existentes. No declara aprobación editorial ni publicación.

Comparación técnica del último cambio conocido: 821758b8 añadía relecturas de originales dentro del presupuesto. No hay evidencia de que esa modificación introdujera las pérdidas anteriores; no se atribuye regresión a Work.

## Muestra estable y ANTES / DESPUÉS

Se mantienen los cinco casos históricos de Luti y el reel exacto. El expediente completo contiene **16 casos**, incluidos bloqueos y un descarte geográfico; no se reemplazan para mejorar porcentajes. El JSON adjunto conserva antes, decisión, fuente, visibilidad y pendiente por caso.

Dos mediciones distintas: (1) reproducción del código base y del corregido sobre **los mismos 11 documentos culturales y dos índices**, con hashes de las respuestas públicas; (2) replay manual acotado de nueve consultas de fuente, capturadas realmente durante esta intervención y guardadas por el escritor staging existente. Las lecturas de archivo no se presentan como nuevas solicitudes HTTP ni como ejecución programada.

| Indicador | Antes | Después comprobado |
|---|---|---|
| Productividad sobre 11 documentos fijos | 2/11 con extracción estructurada de sesión, contexto curatorial o identidad | 9/11; Open House y Casa Yogi permanecen sin extracción útil automática |
| Productividad de adquisición manual | No existe medición homogénea anterior de estas mismas nueve consultas | 7/9 con contenido para revisar; una identidad sin fechas puede ser útil aunque el estado técnico sea index_only |
| 0221, artículo fijo del 31/10 | 0 sesiones | 28 anuncios históricos secundarios; no eventos futuros revividos |
| 0221, replay de tres documentos | 0 listings de esa fuente en el corte inicial | 73 observaciones de fuente, 45 sesiones distintas; repetición entre artículos preservada como evidencia, no como canónicos duplicados |
| Reel exacto Luti | Ausente/no leído; 0 pistas separadas | Caption leído, atribución og:url coincidente, 13 fragmentos/7 secciones literales |
| Luti histórico | 1/5 con listing, 0/5 en agenda API; 0 decisiones | 5/5 referencias conservadas y revisadas, 5 decisiones: 2 descubrimientos, 1 programa de espacio, 2 HOLD |
| Visibilidad de los cinco en agenda | 0/5 | 2/5 como RADAR_UNVERIFIED, publicationApproved=false; Dardo Rocha por memoria del espacio |
| Oferta cultural sin forzar sesiones | Sin los tres campos nuevos | Tres ofertas aceptadas en memoria: Hipódromo/Dardo Rocha, Open House y Residencia Corazón |
| Identidades nuevas | 0 en este lote | Tres candidatas: Muerde, MIGA y Vermú Interferencia; ninguna promovida automáticamente |
| Diversidad del lote | Predominio de programación habitual en la agenda previa | Gastronomía cultural, arquitectura/patrimonio, residencias artísticas, fiestas, teatro comunitario, música independiente y vino; no cuotas ni índice de toda la ciudad |
| Pérdidas | 0221 sin sesiones, El Día sin notas, Luti sin reel exacto | Dos fuentes recuperan contenido; dos originales nuevos llegan a API. Persisten Casa Yogi, truncación Open House y fuentes sin original |
| Integridad | Conflicto previo Carmen 21:00 canónico / 20:00 ticket | Conflicto registrado, sin sobrescritura fuera del writer. Cero canónicos nuevos; Catar conserva su mismo ID; no doble evento por Muerde teatral/festival |
| Cadena operativa | HTTP ok no acreditaba cobertura | run manual identificado, nueve checks, 75 filas de listing nuevas, diez candidatos nuevos, tres campos aceptados y dos descubrimientos verificados por HTTP Vercel autenticado |

La razón 9/11 mide capacidad de extracción sobre documentos disponibles; no es recall de toda la oferta cultural. Las 13 pistas del reel no son 13 acontecimientos ni relaciones aceptadas. La denominación “resuelto” significa decisión editorial emitida; dos de los cinco casos históricos siguen pendientes de prueba primaria.

## Cinco referencias de Luti

| Referencia | Decisión | Evidencia y salida |
|---|---|---|
| La Plata Muerde | Descubrimiento listo para investigar | Organizador → WeVix, 07/11 12:00 Hipódromo; presente en API como no verificado |
| Bocanada aniversario | HOLD | Luti y Genda coinciden en 07/11; “gratis hasta las 23” no acredita inicio. Falta original del organizador/sede |
| Festival Pizza Platense | HOLD | Caption original conserva 12/11. Nota del 08/10 no prueba esa fecha. Proyecto Interferencia candidato, sin relación aprobada |
| Patio / Dardo Rocha | Programa cultural del espacio | Hipódromo confirma 19/11 y jornada cultural gratuita; campo aceptado visible. Patio específico aún secundario, sin evento independiente |
| MIGA | Descubrimiento listo para investigar | Pinta → Passline original, 23/11 16:00 Hipódromo; presente en API como no verificado |

El reel exacto **DfVEIVTSTGu** fue leído por fetch público de Radar aun cuando el buscador no pudo abrirlo. Caption completo y og:url de lutitravelguide quedaron en candidates.evidence. No se exploró el perfil, ni Stories ni una sesión privada; no se atribuye monitoreo automático a la cuenta.

## Resto del expediente

La Trifulca conserva contexto y enlaces al juego propio/AllTickets, pero los originales devuelven shells sin corroboración legible completa de la sesión. Carmen mantiene conflicto horario pendiente de recibo fresco del colector. Casa Dionisio conserva valor como espacio/circuito sin transformar su agenda antigua en novedades. Casa Yogi mantiene el fallo de acceso. Open House permanece festival distribuido; su oferta fue corroborada editorialmente y no acredita que Radar ya interprete su raíz truncada. Catar es control positivo previo, no alta nueva. Residencia Corazón conserva oferta de residencias sin inventar inauguraciones. El Día recupera Sin Telón/La Caterva como pista de teatro comunitario; Chascomús se descarta del alcance local y se conserva como contraejemplo.

## Ejecución, permisos y publicación

- Neon operacional, misma rama/base. Adquisición mediante **poraca_radar_limited_prod**, sin INSERT en canónicos. Se utilizaron las sentencias del save_source_result vigente; no un escritor paralelo.
- Conocimiento mediante **poraca_radar_qa** y poraca_apply_cultural_batch_v1 existente: tres ACCEPTED_FIELD y tres CANDIDATE_RECORDED. Decisiones del expediente en review_log existente; no tablas nuevas.
- Writer de eventos confirmados y sus guardas intactos. Su whitelist no admite estos tickets gastronómicos; no se mintió sobre el rol del origen para forzar aceptación.
- API /api/agenda y /api/cultural-memory, **HTTP 200 autenticado**: Muerde y MIGA una vez cada uno; tres textos nuevos presentes. No se cambió código web ni se necesitó redeploy para reflejar datos.
- Web 0a581ae5, deployment dpl_2xphm2vN4pqrk5Msn2KLviMctM3T READY, SSO all conservado. La lectura HTTP no es QA visual.
- Validación local del lote: 470 pruebas ejecutadas, una omitida, ninguna fallida (469 PASS). Siete pruebas nuevas se concentran en pérdidas demostradas. Sin GitHub Actions, FULL extraordinaria, nuevas ramas, motores, permisos ni cronogramas.

## Continuación exacta

1. Observar en las ventanas ordinarias 05/13/21 ART los cultural_yield y el uso de los permalinks del buzón. El replay manual no acredita autonomía.
2. Bocanada y Pizza: solo reabrir si hay original nuevo; no repetir búsqueda bloqueada ni usar horas de acceso como inicio.
3. Casa Yogi: canal alternativo; Open House: cuerpo truncado antes de contenido. Ambas limitaciones siguen en la muestra.
4. Carmen: próxima relectura ordinaria del original y revisión del mismo ID con writer limitado; no cambio directo a 20:00.
5. #30 queda a Chat: visibilidad DOM y experiencia. No declarar QA visual completado.

## Control de las agendas fundacionales conservadas

Lectura SQL posterior, sin cambiar adaptadores que ya producen datos: Genda conserva161 listings/74 futuros; TeatroCerca20/18; Alpedó119/33; Alternativa10/4. Son observaciones de fuente, no eventos canónicos distintos. Genda/TeatroCerca/Alpedó se conservaron sin parches.

Alternativa requiere seguimiento específico: su raíz pública actual es una interfaz que muestra “Cargando”, sin enlaces obra en el HTML (39.146 caracteres, cero URLs de obra). Las cuatro aperturas del último check proceden de originales de la watchlist ya existente; no prueban descubrimiento de la cartelera completa. El bundle enlazado https://static.alternativateatral.com/js/cartelera2-min.js?1-6 devolvió HTTP200 con una página de195 caracteres “Site Unavailable”, no JavaScript utilizable. Se conserva el bloqueo exacto, sin inventar un endpoint ni desplegar navegador/plataforma adicional. No se incorporó esta revisión como sustituto de ningún caso de la muestra.
