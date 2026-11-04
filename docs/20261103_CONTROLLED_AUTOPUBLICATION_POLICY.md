# Por Acá — Política de publicación automática controlada v1
**Aprobación de principio: 03/11/2026**. Prioridad de producto: descubrir circuito artístico y social, no perfeccionar horarios de entradas. Autoriza diseñar automatización **acotada**, no habilita un bypass del escritor actual o permisos generales.

## Un solo decisor (sin otra arquitectura)
Radar solo observa y escribe a `radar_definitivo`. La decisión de publicación pertenece a **editorial**, usando credencial separada con permisos mínimos, lectura de prueba original y escritura atómica por el escritor autorizado. Neon conserva prueba y canónicos; la API privada lee canónicos aprobados, no staging. La web no toma decisiones editoriales.

**Admisión automática potencial**, cuando todos sean verdad: programa/participantes identificables, día/noche confirmado, sede local aprobada única, anuncio exacto HTTPS original vinculado, origen registrado y habilitado, original visto recientemente, sin cancelación, sin conflictos previos, sin variantes legítimas de función o duplicado canónico ambiguo. **No necesita hora exacta.** Una noche con varias bandas es una programación; otro pase de una obra con horario explícito queda en revisión antes de separar sesiones.

**Decisiones:**
- `AUTO_ELIGIBLE_SHADOW` → pasa filtro para el futuro escritor; **no publica** hasta release explícito. Auditar primero.
- `LINK_EXISTING_SHADOW` → coincide con canónico confirmado, solo se vinculará evidencia idempotentemente sin crear segundo evento.
- `REVIEW` → evidencia secundaria, original genérico, conflictos, sede ambigua, varios pases, falta de revalidación o cualquier dato desconocido.
- `DISCARD` → anuncio vencido, cancelado o accesorio que no constituye evento independiente.

**Criterios que jamás se relajan:** identidad de actor y sede, día de la programación, URL exacta de original y alcance geográfico, estatus/no cancelación, duplicados de programa, firma de rol de publicador y procedencia auditable. No se interpreta portal de ticketera como autoridad para todo su dominio ni un índice genérico como anuncio original. Horarios solo si el original los da; jamás `20:00` por defecto.

## Estado técnico comprobado
- Neon `public.radar_agenda_events.event_time` y `public.radar_v3_source_observations.observed_time` admiten `NULL`. `api/agenda.js` ya devuelve `time:null` sin destruir la ficha. No hace falta cambiar esquema ni web para incorporar una observación sin hora.
- Radar real `src/radar_definitivo.py` no publica; su cuenta de ingesta es una frontera de seguridad que **no se altera**.
- El escritor `public.poraca_apply_cultural_batch_v1` es SECURITY DEFINER y exige referencias de autorización, fuente original, comprobaciones editoriales y colisiones. Algunas rutas aún condicionan aprobación o identidad al reloj. **No editarlo por sustitución de texto**, no activar permisos generales y no reutilizar los `authorizationRef` históricos.
- Un contrato secundario `public.poraca_stage_editorial_observation_v1` existe como fichero SQL en el sitio, pero no está instalado en la base operativa; tampoco da permisos a Radar y requiere revisión manual. No confundirlo con el escritor de canónicos.

## Fases de aplicación y pruebas de salida

**A. Sombra (en este lote).** Política versionada en `data/controlled_auto_publication_policy_v1.json`, evaluador puro `src/radar_controlled_publication_shadow.py`, tests positivos y negativos. No Neon writes, no web deployment, no flag encendido. El evaluador nunca emite `publicationApproved=true` ni una ID canónica.

**B. Integración en staging (siguiente lote, no en esta publicación):**
1. Adaptador que complete los hechos a partir de recibos **originales** con campos de fuente y entidad aprobados. No confiar en flags fabricados por Radar; decisión editorial volverá a cotejar el original y la base.
2. Crear `editorial_auto_decision_v1` en **rama de QA Neon**, default deny, `SECURITY INVOKER` para decisiones y un escritor separado con transacción, rol de mínimo privilegio, advisory lock para mismo acto/día/sede, evento y recibo de idempotencia. Debe reconocer `event_time NULL` y no duplicar por puertas/show ni fusionar funciones genuinas.
3. Ensayar 30 casos reales: casos sin hora, artistas múltiples, anuncio repetido, fuente secundaria, dos funciones legítimas, cancelación, fecha contradictoria, diferente sede, cuenta de Instagram genérica, ticket accesorio. **Cero falsos AUTO** y cero eventos duplicados o publicados durante pruebas.
4. Verificar en QA la continuidad evento original→recibo fuente→decisión→escritura canónica→API y la capacidad de desactivar la publicación sin apagar Radar.

**C. Producción controlada (solo tras certificación B):**
- Feature flag editorial **apagado por defecto**, activar para fuentes originales ya registradas, sedes unívocas, categorías y radios geográficos permitidos. No activar a nivel de todo el dominio de una ticketera.
- Auditoría por lote: conteos `AUTO` / `REVIEW` / `DISCARD` / `LINK`, razones, enlace original, SHA, run_id, fecha de consulta y recibo writer; observar primeros 20 eventos antes de ampliar.
- Publicación en la web solo de `scheduled + confirmed`, sin introducir otra API. Si falla el writer, no hay alta y se conserva el candidato en revisión.
- Cancelación posterior: suspender la tarjeta o marcarla cancelada con referencia oficial, sin borrar histórico.

**Stop/go:** una falla de identidad, duplicación, autorización, cancelación o clasificación equivocada de una publicación obliga a no habilitar modo automático. La nota IICS v1 continúa 5,8: diseñar la política no constituye un PASS adicional. No introducir nuevos servicios, programadores ni Actions por cada fuente.

## Observabilidad y eficiencia
Una ejecución natural de Radar alimenta staging y, cuando el publicador editorial certificado esté activado, procesa candidatos por lote. No reejecutar FULL de demostración, no crear segundo cron ni ampliar rol `poraca_radar_limited_prod`. Para código, un solo QA de GitHub Actions por lote, salvo fallo investigado; para docs, ninguna.
