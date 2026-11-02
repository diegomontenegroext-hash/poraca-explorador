# Por Acá · Cierres verificables 02/11/2026 — fuentes, limpieza web y caso editorial

**Principio transversal:** una fuente puede estar accesible sin entregar nuevas funciones. Una observación puede estar duplicada en varios circuitos sin convertirse en eventos distintos. Una prueba primaria verificable **no equivale** a autorización automática para publicar. No se modificaron canónicos, entidades, relaciones, fuentes operativas ni crons en esta tanda.

## 1. Antifragilidad del lector de fechas: implementado y CI aprobado

[Commit Radar 4ba3947](https://github.com/diegomontenegroext-hash/poraca-explorador/commit/4ba3947e18a433be85459ee03165d70f925671d6); [QA #41435579842](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41435579842), [QA read-only #41435579841](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41435579841): **SUCCESS**.

Se agregó `original_article_publication_day(raw)` para admitir tanto el encabezado visible «DD de mes de AAAA» como formatos HTML estándar `<time datetime="YYYY-MM-DD...">` y `<meta property="article:published_time"...>` (también con atributos en otro orden). La fecha de publicación solo ancla encabezados relativos HOY/MAÑANA de una **nota de agenda real**. No se deduce la fecha de un show por el slug/epoch del enlace, ni por `article:modified_time`, ni desde un vínculo sin fecha. Páginas antiguas, metadatos contradictorios e inválidos quedan excluidos. **Una nota de prensa sigue siendo fuente secundaria; sus funciones quedan en staging `observed_unverified`**.

**Brecha que persiste:** no se ejecutó una FULL nueva después de este cambio, y una fuente web que no enlace la nota o no contenga los campos de función sigue sin producir actividades; no afirmar que El Día ya pasó de index_only a OK. En El Día se comprobó públicamente que `/espectaculos` contiene nota de agenda del 01/11 con actividad para el 02/11; en Centro de Arte UNLP hay un ciclo de bienal 14–28/11 que no debe convertirse en sesiones con horario ficticio; Casa Dionisio conserva en portada antiguas actividades de agosto/septiembre sin fecha inequívoca actual.

## 2. Diagnóstico de 32 fuentes improductivas sin silenciarlas

[Commit Radar 175f4d0](https://github.com/diegomontenegroext-hash/poraca-explorador/commit/175f4d0d513f0dd4cc8123b3e6c7004f3d6b154a), [QA #41435891775](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41435891775) **SUCCESS**.

Las últimas 4 FULL registraron que **32/32 fuentes `index_only` del corte 05:00 persistieron index_only en 4/4**; `0` tuvieron extracciones intermitentes. `src/radar_source_learning.py` ahora añade `sourcePurposeHypothesis` a su reporte de aprendizaje existente, conservando todos los checks y `REPEATED_INDEX_ONLY`. Cuatro colas orientativas por `source_role` declarada:
- `POTENTIAL_DATED_FEED_EXTRACTION_GAP`: portales, carteleras, programación y fuentes originales cuyo contenido puede tener fechas (priorizar El Día, Centro de Arte, Casa Dionisio).
- `REFERENCE_OR_EVIDENCE_REVIEW`: documentos, archivos, acreditación de identidad y comprobaciones de fechas; revisar si justifican fetch periódico antes de proponer cambiar su modo.
- `ACCESS_OR_SCRIPT_BLOCK_REVIEW`: acceso que puede necesitar ruta alternativa legítima y comprobación.
- `PURPOSE_REQUIRES_FIRST_PARTY_CHECK`: casos ambiguos, sin inferir que el sitio es inactivo.

Es una **hipótesis**, no una decisión de cierre. `sourcePurposeCertified=false`, `sourceModeChanged=false`, `sourceModeChanges=0`: no hay auto-disable, no degradación encubierta ni nueva tarea. Las prioridades se ordenan sobre el mismo reporte de Radar; la evidencia de los cuatro días permanece disponible. Una web de identidad sin sesiones futuras puede ser fuente válida para fichas; eso no permite calificarla de productiva como agenda.

## 3. Duplicaciones entre dos canales de investigación: defecto WEB resuelto

La base mantenía **145 descubrimientos crudos** y el conteo de IDs no repetidos también era 145. Una comparación SEMÁNTICA por `title+date+time+venue+original URL` de los 4 lotes paginados (48+48+48+1) encontró **13 pares exactos** `RADAR_DIRECT` vs `EDITORIAL_LEGACY`: eran **132 oportunidades realmente distintas**. Entre ellas `Salsa y No LLores!`, `Viva el Ciclo`, `Dar Paso`, `Malena Muyala`, `Fernando Cabrera & Hugo Fattoruso`.

[Commit web 0e13a09](https://github.com/diegomontenegroext-hash/poraca-lp/commit/0e13a097b0bb24575b813b75348490e52dafc500); [Chromium QA #41436455948](https://github.com/diegomontenegroext-hash/poraca-lp/actions/runs/41436455948) **SUCCESS** — build, vistas 360/390/768/1440, cuatro perfiles de navegación, bandeja móvil con **duplicado en página posterior**, regresión unitaria de exactitud y negativos de horario/sede/fecha/URL distintos.

La web ejecuta `dedupeResearchDiscoveries()` en la presentación antes de filtrar/contar. Prefiere `RADAR_DIRECT` si dos recibos son exactamente la misma función y misma URL; **no es deduplicación fuzzy por título**. No toca el endpoint ni borra auditoría cruda, no cambia el cursor y no interfiere con el catálogo canónico.

**Vercel publicada:** `poraca-lp-privado`, deployment production `dpl_25bhetRdLmAQtRJca431onWJTGRG`, READY, SHA exacto `0e13a097b0bb24575b813b75348490e52dafc500`, alias `https://poraca-lp-privado.vercel.app/`. Conector autenticado verificó SSO ON, HTTP 200 para `/`, `/app.js`, `/api/agenda` y `/api/approved-directory`. `/app.js` publicado efectivamente contiene la deduplicación. **La cifra 132 corresponde al corte observado y al contrato del filtro en JS, no a una captura del Chromium real autenticado en producción**, que sigue pendiente por SSO.

## 4. Caso testigo de admisión editorial: Malena Muyala, aún no publicado

**Origen oficial revisado:** https://casametro.com.ar/evento/malena-muyala/ — **21/11/2026, 22:00, Sala A – Casa Metro, La Plata**; exacto título `Malena Muyala`. Existe en staging Neon `br-mute-recipe-b4odj2bl/neondb`, tres lecturas con **el mismo URL original** (distintas fuentes `source_id`), una cuarta entrada de cartelera de Casa Metro y una observación secundaria de Agenda La Plata:
- `listing_key=d31f182217925163faa51ce53a568e211fe5dc7a888e30006864ef6cfb4686a6`, primera FULL `definitivo-20261102T085408Z-cc1833`, `evidence_tier=primary_venue`, `review_state=observed_unverified`.
- Total **5 registros brutos de fuente** coincidentes por título/día/hora, tres con URL original (sin contar la misma actividad como cinco eventos).
- Función de lectura directa: una identidad Radar `radar-5e20db3a3692571bf0ce69dd43e8f129`, más un lead `obs-manual-casametro-malena-muyala-20261121`; UI ahora los presenta como una sola oportunidad.
- Consulta independiente a canónicos `public.radar_agenda_events` para 21/11, mismo título o URL: **0**; misma sede y reloj 22:00, **0**.

**Acertamos el descubrimiento, origen, horario, sede, reobservación y reconciliación web; NO hemos acreditado la admisión editorial fresca**. Falta un recibo de decisión independiente con actor/procedencia y revisión, el acto de admisión autorizado y el readback canon→API→web, con negativa de otro horario/sala/homónimo. **No realizar INSERT canónico directo** para forzar un semáforo verde. En ningún caso deducir que ya se publicó por el `primary_venue` de staging.

## 5. Siguientes puertas de cierre

1. E2E editorial: procedimiento formal de revisión/admisión de Malena o similar, con recibos e identidad estable, sin fusionar funciones diferentes. Una sola prueba real controlada; no producción masiva.
2. 32 `index_only`: comprobar próxima FULL **después** del nuevo lector de metadatos y de la clasificación de propósito, medir crecimiento real de `OK` de fuentes con agenda (no por reclasificación ficticia). Exigir origen, hora y sede antes de promocionar.
3. Directorio: Pasaje Dardo Rocha y En Eso Estamos aprobados como entidades, pero sin afirmación primaria que habilite minicard Neon; no inventar vigencia. Revisar dos antes de las otras 27.
4. Estabilidad 3/7 días, SSO Chromium real y retiradas de credenciales históricas elevadas siguen independientes; el LOGIN activo nuevo ya demostró ingesta staging.
