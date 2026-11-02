# Por Acá · Recuperación del circuito del vino a partir de Casa Dionisio
**Corte:** 02/11/2026 ART. **Proceso integrado:** `src/radar_source_recovery.py` → `src/radar_category_pulse.py` → `sourceRecovery.historicalNetworkCandidates`. Misma cadena y cron, **sin segundo motor**, sin fuentes nuevas dadas de alta automáticamente ni eventos publicados.

## Diagnóstico operativo (Neon producción, SELECT)

- Fuente `rd-web-56c74fce`, **Casa Dionisio — actividades y vinos**, `circuit=vinos`, `monitoring_mode=fetch`, habilitada, prioridad 75, 0 fallos técnicos. La web / contiene agenda de **agosto y septiembre** pero no prueba eventos fechados futuros en noviembre. `index_only` en cuatro FULL seguidas; **no confundir web HTTP 200 con programación útil**.
- `rd-web-6595ccb6`, página ExpoArte de Dionisio, es fuente de **arte_y_cultura**, no sustituto de la agenda vinos. Inventario `vinos`: **1 fuente fetch**; no encontramos otra fuente activa wine en Neon.
- La exploración `/api/agenda` y Neon no encontró `Feria Catar V Edición` del 27/11, **0 canónicos + 0 staging** al corte; es un lead corroborado *fuera* de la cadena de Radar, no un hallazgo de Radar ni una publicación autorizada.

## Archivo que reconstruimos

El repositorio guarda **10 registros de evidencia: 9 anuncios históricos y 1 anuncio futuro**, en `data/historical-circuit-network-v1.json`. Tras normalizar alias Golden Wine, Villa Wine y Terruño, hay **17 identidades distintas**: **14 de la región LP/Berisso/Ensenada y 3 fuera de la ciudad**. Son **candidatos de organización y seguimiento**, NO 17 fuentes verificadas ni 17 eventos.

1. **Sunset Wine Mixology (2025)**, [0221](https://www.0221.com.ar/que-hago/la-sunset-wine-mixology-vuelve-la-plata-mas-40-bodegas-una-degustacion-lujo-n116918): confirma que **Casa Dionisio, Golden Wine, Villa Wine y Terruño** integraban 4V. Un [anuncio original de 2026](https://www.casadionisio.com.ar/sunset-wine-mixology) dice 4V y además **menciona postergación por lluvia**. NO afirmar que ocurrió ese 10/04 ni trasladar automáticamente a 2026 la identidad individual de los cuatro organizadores de 2025.
2. **Feria BEBER (2026)**: [ticketera original Cámara Platense](https://compras.evento-simple.com/feriabeber/eventos/feria-beber-e1/v2) marca **10/07 20:00**, Casa Frawens, finalizado. Algunas notas publicaron 11/07; **queda registrada la discrepancia y prevalece la fecha original** para un expediente fechado. La [nota de participantes 2026](https://tucoweb.info/se-viene-la-tercera-edicion-de-la-expo-vinotecas-beber-2026/) permite redescubrir, entre otros, Villa Wine, Terruño, Galpón de Vinos, Assemblage, Chapeau, Orujos, Vinoteca City Bell y Don Santiago. No convertir participación histórica en canal activo probado.
3. **Cena Huentala Wines 27/08**, [cartelera histórica del anfitrión](https://www.casadionisio.com.ar/degustaciones): identifica la bodega invitada, no anuncia nueva cena para noviembre.
4. **Pinamar Wine Week 25–27/09**, [oferta histórica](https://compraenlaplata.com/producto/viaje-a-la-pinamar-wine-week): identifica a Viajar & Beber, Santa Narcisa y bodegas visitadas. Son relaciones **de enoturismo**; no se convierten en actividades de La Plata por venir nombradas allí.
5. Otros anuncios preservados incluyen **Noche de las Vinotecas 17/04** [ticketera](https://compras.evento-simple.com/casadionisio/eventos/la-noche-de-las-vinotecas-en-casa-dionisio-e3) y la apertura de la cava 21/08 [registro de publicaciones](https://www.findglocal.com/AR/La-Plata/126149450766795/Casa-Dionisio). Ninguno se reutiliza como evento futuro.

## Nuevas fuentes a investigar por prioridad

**A. Organizadores originales del circuito (alta prioridad).**
- **Cámara Platense de Vinotecas y Afines**, organizadora de BEBER; cuenta pública identificada **`@camaraplatensedevinotecas`** por prensa local (ver [nota](https://www.novabonaerense.com/nota.asp?id=58313&id_tiponota=60&t=VIDEO-Feria-Beber-en-La-Plata-una-experiencia-unica-para-los-amantes-del-vino-y-la-gastronomia)). Antes de crear un `fetch`, verificar canal controlado por la asociación y una **nueva actividad con original, fecha, sede y hora**. Si sólo hay redes sociales inaccesibles, monitoreo limitado o `discover_only` con detección de falta de acceso; nunca asumir que el perfil completo se puede raspar.
- **ACSBA / Asociación Civil de Sommeliers de la Provincia de Buenos Aires**, cuenta **`@sommeliersdebuenosaires`**, entidad independiente del histórico de Dionisio. Su [Feria Catar V Edición 2026](https://www.passline.com/eventos/feria-catar-v-edicion) tiene prueba de venta directa **viernes 27/11, 19:00–23:00, Paseo Mitre, Gorina**. La conexión está dada por el **mismo circuito**, no por una colaboración con Dionisio. Caso de alta editorial individual, en cola; no insertar un canónico por SQL sin recibo autorizado.

**B. Organizadores potenciales de 4V (prioridad alta/media).** **Golden Wine, Villa Wine y Terruño**, nombres históricamente demostrados. Localizar y certificar su canal actual, sin inventar URL ni asumir que siguen coorganizando eventos.

**C. Red ampliada (siguiente lote).** Galpón de Vinos, Assemblage, Chapeau, Orujos, Vinoteca City Bell, Don Santiago, etc.; las bodegas participantes y proveedores fuera de la región se mantienen como relaciones de contexto, no fuentes que deban producir eventos platenses diarios.

## Cambio de código y QA

Se consolidó la investigación **en la infraestructura histórica que ya existía** (no módulos ni carpetas paralelas):
- `data/historical-circuit-network-v1.json`: pruebas enlazadas, asociaciones reales, evento próximo independiente, discrepancia de fecha y **alias de tres vinotecas conciliados**. Eliminada la afirmación de fecha 04/08 de un curso cuya fecha no estaba acreditada; no predicciones.
- `src/radar_source_recovery.py`: reconocimiento de localidades de la región (La Plata, Gorina, Gonnet, Berisso, Ensenada, City Bell, etc.), sin exigir que los actores estén en el casco urbano; traslada `accountHint` al expediente, **no lo transforma en URL verificada**.
- `tests/test_radar_source_recovery.py`: la asociación futura ACSBA tiene prioridad de revisión; socios históricos no son fuentes en producción, no proponer la propia Dionisio como reemplazo, tres alias no duplican identidades, los eventos históricos no reviven después de su fecha. [Última QA de Radar](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41444324188) **SUCCESS**.
- Los informes corrientes de Radar ya incluyen `sourceRecovery.historicalNetworkCandidates`. **No se creó ningún cron, no se cambió la frecuencia, no hubo Neon DML, no se deshabilitaron fuentes, no se publicó ni un evento**.

## Gate siguiente (medible en próximas FULL normales)

- Verificar que `vinos` se encuentre entre los circuitos sin fuentes productivas y que su cola contenga Cámara Platense / 4V y **ACSBA con evento futuro**.
- Auditar al menos **dos canales controlados por organizaciones** independientes de Dionisio y extraer una actividad futura con *fecha + hora + sede + original*; si sólo muestran noticias viejas, mantener estado `NO_PROVEN_FEED`.
- Caso Feria Catar: confirmar no duplicado, abrir expediente editorial, generar recibo de aprobación independiente, y solo entonces consultar la proyección del evento en API/web. Ningún evento confirmado se inventa a partir de la periodicidad anual de la feria.
- Medir en cada FULL: fuentes activas con rendimiento real de vino (base **0/1**), fuentes sustitutas validadas (base **0**), nuevas actividades futuras wine detectadas vía Radar (base **0**), candidatos documentados (base **17 entidades**, **1 original próximo externo**). El objetivo es **redundancia real**, no que una única agenda vuelva a imprimir fechas por casualidad.

**Estado global:** GRAFO HISTÓRICO RECONSTRUIDO Y CONECTADO AL REPORTE = ✅; FUENTES SUSTITUTAS PRODUCTIVAS = ❌ aún sin prueba; EVENTO FUTURO ORIGINAL LOCALIZADO = ✅, INGRESA A PROCESO EDITORIAL, NO PUBLICADO.
