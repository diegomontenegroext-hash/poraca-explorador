# POR ACÁ · CERTIFICACIÓN INTEGRAL PUNTA A PUNTA · V1 · 31/10/2026

**Estado del certificado: NO CERTIFICADO GLOBALMENTE.** Documento reproducible para decidir por evidencia, no un plan sin ejecución. Fuente de verdad: `sql/20261031_certificacion_punta_a_punta_readonly_v1.sql` (ejecutado con Neon autenticado en rama operativa), `src/radar_certification_matrix.py` (46 casos, 13 puertas) y `tests/test_radar_certification_matrix.py` (15 tests controlados en el QA existente). **No se ejecutaron nuevas FULL ni escrituras SQL ni deploys.**

## 1. Política de evaluación: cuatro resultados
- **PASS**: la funcionalidad concreta superó un test EJECUTADO en el ámbito declarado. Un test sintético demuestra contrato, NO funcionamiento vivo.
- **FAIL**: resultado real incumple condición observable. Es un hallazgo, no necesariamente un defecto de infraestructura.
- **BLOCKED**: falta acceso autorizado o implementación imprescindible; no convertirlo en PASS/FAIL especulativo.
- **NOT_TESTED**: sin prueba empírica suficiente en el entorno/fecha relevante.
- **NO CERTIFICADO GLOBAL** mientras alguna puerta crítica no tenga PASS demostrado. CI PASS de fixtures no implica cadena cultural certificada.

## 2. Corte verificable del 31/10 (Neon real)
- Última FULL `definitivo-20261031T125338Z-5e96bb`: finalizada, **63/63 fuentes seleccionadas**, 39 OK y 24 `index_only`, salud **PARCIAL**. Los 63 incluyen fuentes y semillas según selección, no representan los 228 perfiles efectivamente leídos.
- Inventario: **62 fetch, 123 discover_only y 43 review**. Perfil Instagram `discover_only` no implica que se haya visto su último reel/audio/carrusel.
- Staging **371 observaciones**, de ellas **315 actuales/futuras**, **83 marcadas primary con fecha, hora y sede** (necesitan cotejo de original y no equivalen a 83 admitidas).
- **0 observaciones** tocadas en `public.radar_v3_source_observations` después de esa FULL; **0 canónicos futuros**, **0 futuros confirmados/publicados**. El HTTP vivo de `/api/agenda` y Chromium SSO **NO SE PROBARON** en este corte. Vercel READY con SSO no sustituye HTTP.
- **15 asociaciones sospechosas** de tickets recomendados de otros eventos siguen en staging sin promoción. Corrección de extracción integrada con QA en PR #13; hay copia de recuperación, pero la limpieza selectiva activa quedó bloqueada.
- Conservación: **677 observaciones y 40 eventos futuros del corpus previo** archivados bajo `radar_archive_20261031`; 121 eventos históricos permanecen en el canónico.
- No hay ninguna fuente `fetch` inequívocamente identificada como la programación de Deportes UNLP en el inventario observado. Existen fuentes de clubes dispersas, algunas solo `discover_only`. Es evidencia de una **laguna de cobertura** para descubrir actividades recreativas no ligadas a un evento fechado.

## 3. Muestreo adversarial representativo, sin convertir nombres en reglas

| Caso vivo y fuente | Qué evidencia existe | Qué debe demostrar el Radar | Resultado en este corte |
|---|---|---|---|
| Agenda cultural agregadora (Genda) | Cartelera pública por días y rubros, pistas secundarias | Recuperar detalles y distinguir originales, cambios, duplicados y fechas | PARCIAL: ingestión sí; original y cobertura no certificados |
| Plataforma teatral (Alternativa Teatral) | Fichas con funciones, salas, días y horarios | Varias funciones sin fusionarlas; revalidación desde originales específicos | PARCIAL: tests y ejemplos; sin canónico futuro |
| Curaduría audiovisual (Luty) | Cuenta inventariada en canales indirectos; no auditamos reel+audio actual | Detectar reel, caption, carrusel o nuevo canal, con acceso permitido | NOT_TESTED: no afirmar última publicación procesada |
| Prensa (El Día / 0221) | Respuesta web OK repetida, cero sesiones detectadas en recientes `source_outcomes` | Buscar nota de agenda, releer estructura, distinguir noticia de sesión | FAIL de extracción, NO de relevancia del medio |
| Centro cultural/institución | Links accesibles sin sesiones concretas | Preservar entidad, enriquecer actividades permanentes, detectar cambios de agenda | PARCIAL / sin demostración de actualización viva |
| Deportes UNLP | Fuente pública documenta kayak polo, ajedrez, hockey, actividad regular con horarios | Descubrir fuente y nuevos grupos, crear propuesta de actividad/entidad sin inventar función fechada | FAIL de cobertura/alta dinámica; fuente no monitoreada activamente |
| Venta de entradas individual | La ficha recomienda otros eventos ajenos | No atribuir funciones recomendadas al organizador de la ficha | FAIL histórico en staging (15 asociaciones); prevención futura probada en fixture |

**Ejemplos externos contrastados sin insertar en Neon** (no constituyen corrida de Radar): 
- https://agendalaplata.ar/teatro
- https://www.alternativateatral.com/espacio5168-teatro-el-escape
- https://www.deportes.unlp.edu.ar/articulo/2026/3/5/otras_actividades
- https://unlp.edu.ar/gestion/bienestar_universitario/propuestas-recreativas-y-deportivas-para-estudiantes-126741/

## 4. Matriz de 46 situaciones y cómo certificarla

El inventario **completo y versionado** `CASES` está en `src/radar_certification_matrix.py` (C01–C46). Cada caso indica el tipo de evidencia requerido; no se puede certificar con una simulación cuando exige prueba de cuentas reales.

**A. Descubrimiento y salud (C01–C09).** Una sola tarea, sin carreras ni doble cron; nueva fuente desconocida; menú renombrado; caída del referente y recuperación por otro; 403/429/captcha; `ok` sin extracción; fuente sin historial; original vs espejo; cuota exploratoria por escena. Casos C02/C03 cuentan con fixture; C04/C05/C07/C09 requieren prueba controlada + evidencia de comportamiento vivo.

**B. Formatos y canales (C10–C19).** JSON-LD, HTML de múltiples funciones, RSS/Atom, ICS genérico, JS, migración HTML↔ICS, imagen/afiche, reel audio+caption, carrusel y contenido retirado. El ICS real hoy está **anclado a un festival**: NO confundir 24 sesiones reales de Freezer con "ICS universal certificado". Luty no puede darse por cubierta por solo tener su perfil.

**C. Semántica cultural (C20–C32).** Actividades habituales; grupo deportivo; centro cultural nuevo o actualizado; múltiples horarios; reprogramación; cancelación; cambio de sede; dos fuentes de la misma función; showtimes distintos; recomendaciones de tickets; sede desconocida; secundarias sin original. El parser que no inventa "clase todos los jueves" como evento está bien; **todavía falta guardar esa clase como oferta regular/entidad cultural**.

**D. Persistencia, aprendizaje y auditoría (C33–C36).** Idempotencia, archivo, score por aporte vs HTTP OK y huella de cambio de formato. Requerir ID de fuente, canal, versión de estrategia, URL original, momento y decisión, con costo y rollback. No premiar visitas sin función ni castigar museo por no programar funciones diarias.

**E. Conversión, API y experiencia (C37–C44).** Staging→observación, conflicto aislado, no autopublicación, canónico autorizado, API autenticada, SSO/Chromium, home hoy/mañana y búsquedas por música under, fiestas/vinos, yoga, cerámica, deporte. Si **C37 o C40 fallan**, ninguna prueba de apariencia web compensa la falta de eventos reales.

**F. Operación (C45–C46).** Revertir un selector sin pérdida, comprobar un único cron, pruebas 3/7 días sin confundir estabilidad con volumen. Mismo presupuesto de requests y ventanas ART.

## 5. Prueba integral reproducible: orden y evidencias

1. **QA determinista sin red**: `python3 -m unittest discover -s tests -v` desde el workflow CI existente. El archivo de certificación agrega 15 pruebas de fixture y gates; las pruebas Radar previas cubren 24 sesiones ICS reales, duplicación, zonas horarias, ranking y presupuestos. Etiquetar como `FIXTURE_PASS`, no LIVE_PASS.
2. **Neon SELECT**: ejecutar `sql/20261031_certificacion_punta_a_punta_readonly_v1.sql` contra `frosty-union-52906378` / `br-mute-recipe-b4odj2bl` / `neondb`. Guardar `run_id`, horario, SHA, conteos, 15 sospechosos y estado por puerta; no mutar mientras certifica.
3. **Cuentas y fuentes reales elegidas por diversidad**: agenda amplia, teatral, prensa, reel audiovisual, centro cultural, oferta regular, deporte y sitio nuevo. Cotejar en la publicación original 3–5 hechos por fuente. Si la plataforma bloquea audio/caption, marcar `BLOCKED_ACCESS` y medir fuentes alternativas; nunca inferir que se leyó.
4. **Fallos inyectados en fixtures**: portal 403/429; enlace cambia; HTML vacío; agenda salta a ICS; origen fuera de ciudad; duplicado espejo; venue contradictorio; evento cancelado; publicación multimedia inaccesible. Comparar lo esperado con la salida real: identificación correcta, falta explicitada, alternativa intentada y preservación de memoria.
5. **Neon editorial**: construir expediente por caso con identidad, prueba y estado. Una duda queda en HOLD individual; validar paso de al menos una sesión aprobada por vía autorizada a canon y API. Nunca autorizar escritura automáticamente por el test.
6. **Web protegida**: HTTP autenticado y Chromium con identidad permitida en el deployment actual, sin desactivar Deployment Protection ni fabricar un URL público. Demostrar agenda futura y navegación de perfiles, no solo READY.
7. **Seguimiento**: ejecutar el mismo protocolo con las **corridas ordinarias ya programadas** durante al menos 7 días, sin runs artificiales ni nuevos cron. Certificar degradación y recuperación por fuente/estrategia.

## 6. Bloqueos de certificación y prioridad (no solo mejoras de UX)
- **P0-A**: recuperar/normalizar el flujo a observación editorial y canónico futuro; actualmente roto después del reset.
- **P0-B**: aislar las 15 asociaciones cruzadas en los SELECT de aprobación y verificar que no reaparezcan en nuevas ingestas.
- **P0-C**: selector de estrategias por contenido + fallback JS/feed/social accesible y detector de degradación/reemplazo por entidad; faltan casos reales de fuente que desaparece.
- **P0-D**: elevar deporte, yoga, cerámica y actividades permanentes a objetos/relaciones de primera clase sin convertir reuniones recurrentes en fechas inventadas.
- **P1**: pruebas protegidas de API/SSO, enriquecimiento de fichas, medidor de cobertura por intención y tres rondas de estabilidad.
- **P1**: incorporar reportes de fallas accionables por fuente: `UNAVAILABLE`, `FORMAT_CHANGED` sólo con huella comparada, `NO_DATED_SESSIONS`, `INSTITUTIONAL_REFERENCE`, `ALTERNATIVE_CHANNEL` verificado.

**Criterio de salida:** todas las puertas críticas en PASS *real*, 0 publicación indebida, 0 atribución cruzada, fuente caída recuperada al menos una vez con método general, eventos futuros aprobados visibles en API+web SSO, y cobertura diversa demostrada sin depender de una sola agenda. Hoy NO se alcanza.
