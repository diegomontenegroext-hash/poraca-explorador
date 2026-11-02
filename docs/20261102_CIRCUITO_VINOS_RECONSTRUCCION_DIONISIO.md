# Por Acá · Reconstrucción histórica del circuito vinos (piloto Dionisio)
Fecha: 2026-11-02 · La Plata (ART) · Modo: investigación y recuperación de fuentes, NO publicación.

## Problema demostrado
Neon PROD `frosty-union-52906378 / br-mute-recipe-b4odj2bl / neondb`: el circuito `vinos` tenía **una única fuente `fetch` habilitada**, `rd-web-56c74fce`, `https://www.casadionisio.com.ar/`; su rendimiento fue `index_only` en las últimas cuatro FULL. Otra URL ExpoArte de Dionisio está clasificada bajo `arte_y_cultura`, no bajo vinos. Cero eventos canónicos o registros staging con "Catar" o "Dionisio" y fecha futura al inicio de este relevamiento. No concluir que la vinoteca cerró, ni que todos los circuitos de vinos cesaron: portada con agosto/septiembre, subsecciones y contenidos históricos activos por separado.

## Cómo reconstruimos, conservando procedencia
| Histórico documentado | Actores que aparecen | Prioridad tras hallar la publicación |
|---|---|---|
| Dionisio · cena Huentala, 27/08/2026 | Bodega Huentala Wines | Cuenta/sitio de bodega a comprobar cuando venga a LP; radicada en Mendoza, NO agenda platense recurrente |
| Dionisio · Sunset Wine Mixology 4V, 10/04/2026 y edición 17/10/2025 | 4V, Golden Wine, Villa Wine, Terruño, Dionisio | Otras tres vinotecas ORGANIZADORAS locales; buscar su canal oficial y fechas nuevas; no inventar cuentas |
| Dionisio · escuela y taller, agosto 2026 | Escuela Argentina de Sommeliers | Fuente de talleres y cursos (sede LP se verifica por anuncio original, escuela de alcance nacional) |
| Dionisio · participación en BEBER julio 2026 | BEBER Expo de Vinotecas; organizador identificado en prensa: Javier Coirini | Investigar productor/evento y participantes, sin asumir nueva edición |
| Dionisio · viaje Pinamar Wine Week septiembre 2026 | Viajar & Beber, Bodega Gamboa, Antiguo Legado | Organización de experiencias que SALEN de La Plata; bodega como socio, no origen de eventos locales diarios |
| Bunker · curso de vinos nivel 2, octubre 2026 | Bunker La Plata | Sede local asociada al circuito independientemente de Dionisio; comprobar continuidad por fuente oficial |
| Independiente: Feria Catar 2025 y venta de V edición 2026 | Asociación Civil de Sommeliers de Buenos Aires (ACSBA) | PRIMER ANUNCIO FUTURO REAL localizado; original en Passline, organización y perfil público identificados |

### Fuente futura concreta (NO publicada automáticamente)
**Feria Catar V Edición — viernes 27/11/2026 de 19:00 a 23:00 — Paseo Mitre, 485 y 138, Gorina, La Plata.** Ticketing original: https://www.passline.com/eventos/feria-catar-v-edicion (Asociación Civil de Sommelier de Buenos Aires). Fuente de series previas 2025 y cuenta citada: https://www.eldia.com/nota/2025-11-6-3-47-58-llega-la-feria-catar-al-paseo-mitre-de-gorina-gourmet y perfil https://www.instagram.com/sommeliersdebuenosaires/. El evento no figura en los canónicos actuales ni en staging `Catar` al corte. **Preparar ingreso por flujo de revisión autorizado; no INSERT manual ni aprobación inferida.**

### Canales descubiertos
- https://www.casadionisio.com.ar/degustaciones — hospedador, fuente de archivo de actividades (no agenda noviembre).
- https://www.instagram.com/dionisio_vinoteca/ — perfil nombrado en tienda oficial https://www.tienda.dionisioonline.com.ar/.
- https://www.instagram.com/sommeliersdebuenosaires/ — cuenta citada por El Día para feria Catar 2025; verificar que mantenga agenda propia en vez de asumir productividad.
- https://www.passline.com/eventos/feria-catar-v-edicion — anuncio futuro con fecha y sala en fuente de ticketing.
- https://sommeliers.com.ar/ — sitio de EAS (formación nacional, actividades de LP solo con programa comprobado).
- https://huentalawines.com.ar/ — bodega invitada, no fuente regular de eventos platenses.
- https://www.casadionisio.com.ar/sunset-wine-mixology — feria 4V y listado de numerosas bodegas. Todas ellas son *relaciones históricas*, no 40 fuentes automáticamente activadas.
- https://www.0221.com.ar/que-hago/la-sunset-wine-mixology-vuelve-la-plata-mas-40-bodegas-una-degustacion-lujo-n116918 — identificación en prensa de Golden Wine, Villa Wine y Terruño; **cuentas oficiales individuales pendientes de validación**.
- https://realpolitik.com.ar/nota/73179/feria-beber-la-plata-es-la-ciudad-con-mas-vinotecas-por-habitante-del-pais/ — entrevista del organizador BEBER, sin enlace oficial suficiente para alta de fuente.

**Importante:** `dionisiocasadevinos.com` corresponde a una empresa de Córdoba y **NO es Casa Dionisio de La Plata**. Tampoco debe confundirse `Espacio Dionisia` cultural con la vinoteca. No hacer unión por similitud del nombre.

## Cambio general ya integrado
[Datos rastreables](../data/historical-circuit-network-v1.json) y [recuperación general](../src/radar_source_recovery.py), conectada con el **mismo** pulso [category_pulse](../src/radar_category_pulse.py).
- Ante `REPEATED_INDEX_ONLY`, `RECENT_YIELD_DROP` o `SUCCESSFUL_FETCH_ZERO_DATED_SESSIONS`, primero mide fuentes efectivamente productivas del circuito.
- Si falta cobertura, recoge vínculos históricos auditados, encuentra *organizadores, aliados, series y canales* y los ordena. Reconoce eventos actuales únicamente cuando existe registro `upcoming_original` con fecha explícita, URL original y localidad relevante.
- Un circuito SIN ninguna fuente productiva y CON un anuncio futuro verificable se prioriza sobre otros `index_only` sin señales recientes, aun con límite top-N.
- El resultado `sourceRecovery.actions[].historicalNetworkCandidates` aparece en el **informe existente** después de la FULL ordinaria. No crea otro cron, repositorio, tabla, rama, fuente fetch, sesión ni evento canónico.
- `sourceAutoEnrolled=false`, `publicationApproved=false`; un registro histórico nunca se recicla a fecha futura. Tras 27/11, el candidato deja de considerarse futuro sin cambio manual de fechas. Un socio de Mendoza no es fuente platense automáticamente.
- QA `tests/test_radar_source_recovery.py` con negativos para URLs no HTTPS, contexto de circuito distinto, eventos vencidos, prohibición de alta/publicación y prioridad de circuitos sin cobertura. [GitHub CI #41443681853](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41443681853) SUCCESS.

## Qué no está cerrado todavía
1. Revisar una a una las URLs oficiales de las otras vinotecas 4V y la continuidad de BEBER; no adivinar handles de IG a partir del nombre.
2. Pasar Catar 27/11 a *pista real de revisión* mediante mecanismo autorizado, luego corroborar en bandeja/API y sólo publicar tras admisión editorial individual.
3. Ejecutar una FULL NATURAL con la versión nueva y comprobar en `sourceRecovery` que el circuito vinos aparece primero entre fuentes sin rendimiento, con evento 27/11 como ORIGINAL SIN PUBLICAR. Contabilizar fuentes efectivas del circuito (previo: 1 y 0 productivas) y repetir en más circuitos con fuentes envejecidas.
4. Evolucionar de semillas históricas corroboradas manualmente a extracción de nombres/enlaces desde publicaciones pasadas cuando haya HTML o medios disponibles y verificables. No afirmar autocuración completa cuando hoy solo existe reconstrucción inicial versionada.

### Criterio de certificación futuro
`RECOVERED_SOURCE_DISCOVERY` requiere una segunda URL original con actividad vigente, observación obtenida por Radar y evidencia de extracción/ingesta medida. **La Feria Catar encontrada por investigación externa y guardada como pista NO alcanza todavía ese nivel**. No maquillar el semáforo ni desactivar Dionisio; conservarlo como referencia válida para su propia agenda y relaciones.
