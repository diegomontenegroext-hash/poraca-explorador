# Por Acá — contrato de Radar adaptativo y aprendizaje de fuentes
**Propuesta arquitectónica registrada: 31/10/2026 · Estado: hoja de ruta para implementación y validación incremental, NO funcionalidad desplegada.**
**Backlog dueño:** `diegomontenegroext-hash/poraca-lp#28` (Radar), relacionado con #16.
**Ejecutor:** `poraca-explorador`, dentro de la arquitectura y orquestación existentes.

## 1. Problema comprobado y decisión
Radar tiene inventario, historiales por fuente, deduplicación propuesta, staging y QA, pero **no aprende todavía qué fuente merece qué esfuerzo ni cómo cambiar la estrategia de extracción cuando su forma de publicar cambia**. Los `special_links` y adaptadores por dominio dan cobertura puntual, pero no deben convertirse en estrategia principal. El código elige `monitoring_mode='fetch'`, ordena por última consulta/prioridad asignada, y usa cadencias y backoff. `index_only` acelera la próxima visita a `min(12,cadence_hours)` aunque la página pueda ser institucional sin funciones. Además la FULL actualmente vuelve a incluir todas las `fetch`, no discrimina utilidad. La fuente `Centro de Arte UNLP` o `Casa Dionisio` puede cambiar su navegación en tres semanas sin que Radar descubra el nuevo formato por sí solo.

**Nueva regla:** mantener adaptadores particulares como último recurso excepcional y temporal. La solución principal será **descubrimiento genérico + selección dinámica de estrategias por contenido + aprendizaje de rendimiento + detección de deriva + memoria con trazabilidad**. No hacer más ajustes de dominio sin anotar cuál patrón generalizable faltaba y si puede cubrir más de una fuente.

## 2. Tres identidades y un valor editorial
Distinguir expresamente:
- **Entidad cultural**: lugar, persona, colectivo, organizador y programación permanente. Puede merecer una ficha aun sin un solo evento fechado.
- **Fuente/endpoint**: URL, feed, cuenta, agenda secundaria, noticia, calendario; no equivale necesariamente a la entidad o al organizador. Un lugar puede tener varios canales y cambiar su canal preferido.
- **Sesión/evento**: título, fecha local, hora, lugar, fuente original y estado editorial; múltiples horarios son funciones distintas y no deben fusionarse.

El valor de una fuente **NO** es sólo número de links, respuestas HTTP 200 o volumen de títulos. Es su aporte marginal de **eventos nuevos reales verificables**, cobertura de disciplinas poco cubiertas, evidencia primaria, corroboración útil y confiabilidad, frente a solicitudes/tiempo. No penalizar la fuente de yoga que publica clases regulares sin funciones fechadas: aporta información de entidad/actividades permanentes, no necesariamente eventos.

## 3. Catálogo reutilizable de estrategias
El selector observa **la página y sus señales**, no una lista fija de nombres de instituciones.
- `structured`: JSON-LD Event, microdatos de evento y enlaces primarios con fecha local.
- `feeds`: RSS/Atom, ICS y feeds/calendarios públicos *descubiertos desde enlaces reales*.
- `html`: tarjetas, encabezados, enlaces a detalle, fechas explícitas y sesiones múltiples; rutas de un segmento o más sin asumir que son eventos.
- `calendar`: agendas por día/mes, paginación, parámetros explícitos, carga dinámica observada. Nunca inventar URLs no enlazadas ni ampliar el presupuesto de dominio.
- `browser`: fallback acotado cuando hay evidencia de JS y falla la lectura HTTP, respetando límites y tasa.
- `secondary`: agendas generales, prensa, curadores y publicaciones sociales públicas exactas; pistas que **requieren verificación de la fuente original**.
- `institutional`: especialidad, horarios regulares y actividades permanentes de entidades. Mantener como contexto; no fabricar función por nombrar «agenda», «taller» o «degustaciones».

Seleccionar estrategia por señales (links, tipo de contenido, fecha y evidencia) y memoria del rendimiento de esa estrategia por fuente; mantener una excepción acotada solo cuando hay prueba de que el genérico no alcanza. Las excepciones tienen causa, fecha, regresión, versión y criterio de retiro.

## 4. Memoria y aprendizaje progresivo
Registrar, por `source_id` y versión de estrategia, historial de 7 y 30 días:
1. URLs visitadas, status HTTP, 429, tiempo y presupuesto consumido.
2. Fechas/sesiones extraídas, distintas, nuevas, reobservadas, conflictos y errores; distinguir fuente secundaria de original.
3. Cantidad corroborada por original, evidencia completa, eventos que efectivamente fueron aprobados más adelante (atribuibles) y contribución marginal; **nunca contar aprobación no ejecutada**.
4. Tasa de duplicación entre fuentes y cobertura por **disciplina del evento** y tipo de entidad, no categoría del dominio.
5. Huella del formato: enlaces/estructura/feed presentes; diferencia de plantilla, disminución súbita de rendimiento o desaparición de secciones.
6. Decisión de próxima revisión, motivo y alternativa probada, con versión y reversión.

Primera implementación: **scorecard solo lectura** que compara estrategias y rendimiento sin cambiar prioridades/cadencias. Después, política determinista reversible (versionada), calibrable con muestras auditadas. No utilizar LLM por cada URL: reservar análisis semántico y diagnóstico profundo para anomalías, casos con alto valor o fuentes nuevas. No dejar que una sola jornada o una fuente nueva sin histórico determine su reputación.

## 5. Asignación dinámica del presupuesto
Una única tarea 05 FULL / 13 y 21 incremental. **No crear nuevos cron, bots, ejecutores ni pipelines**.
- **Explotación:** reservar mayor parte de solicitudes a fuentes con eventos vigentes, original útil y contribución marginal demostrada.
- **Exploración:** reservar cupo estable para fuentes nuevas, recuperaciones, circuitos poco cubiertos, fuentes inactivas y consultas ocasionales de referencia; evitar «solo gana quien ya es popular».
- **Cambio de canal:** ante enlace obsoleto o cambio de formato, intentar estrategias generales alternativas dentro del presupuesto y registrar qué funcionó, sin inventar URL, fechas o publicaciones.
- **Degradación gradual:** si un endpoint no aporta eventos, bajar su frecuencia y probar otros canales de la misma entidad. No borrar la entidad ni excluirla definitivamente. Si reaparece en Genda/Al Pedo/u otro original, reevaluar el canal.
- **Reactividad:** cambio real en el contenido/estructura o confirmación externa puede aumentar temporalmente frecuencia; 429 y fallos técnicos generan backoff. `index_only` reiterado **no debe generar reintentos frecuentes permanentes**.
- **FULL inteligente:** conservar barrido diario de cobertura prioritaria y revisión periódica rotativa de cola larga; no fingir que «FULL» significa visitar toda URL diaria si el presupuesto y el valor editorial no lo justifican. Antes de modificar esta semántica, mantener el contrato actual y comparar en modo sombra.

## 6. Ejemplos que deben pasar
**Casa Dionisio:** si su web publica eventos hasta noviembre y luego solo novedades en otro canal, Radar detecta caída de sesiones + señales del nuevo canal, prueba estrategias disponibles y reevalúa el peso de cada endpoint. La ficha del lugar sigue existiendo. Si durante 30 días no hay función con fecha verificada, no debe consumir la misma frecuencia que una agenda activa; tampoco quedar invisible para siempre.

**Centro de Arte UNLP:** si cambia rutas o la plantilla, no depender de `/calendario-2/` ni parches manuales; el descubridor busca enlaces actuales y formatos accesibles dentro del mismo presupuesto. Si solo publica información institucional, aprende a utilizarlo como referencia de entidad.

**Nueva fuente desconocida:** entra en observación; un reconocimiento genérico prueba formatos y encuentra funciones o actividades. La fuente se incorpora a la lista activa **solo con evidencias y controles**, y su prioridad se ajusta por su rendimiento posterior; la revisión humana se reserva para relevancia/identidad ambigua y admisión editorial.

**Genda / Al Pedo:** su volumen es pista de descubrimiento, no métrica de excelencia. Múltiples agendas pueden corroborar una sesión; se mantienen enlaces de fuentes cruzadas sin crear eventos confirmados artificialmente.

## 7. Implementación y puertas de aceptación
**Fase A (próxima):** lectura comparativa de 7/30 días por fuente + tipo de canal + métricas de calidad/costo; clasificación `agenda_activa`, `referencia_institucional`, `canal_incompleto`, `desconocida` como **hipótesis observable, no edición automática de fuentes**. Corregir interpretación de `index_only` en el informe antes de cambiar frecuencia.

**Fase B:** biblioteca de estrategias genéricas y selector sombra que produzca diagnóstico y candidato de estrategia sin modificar ingesta normal; regresión sobre el mismo conjunto de URLs con formato variable y fuente nueva. Mantener excepciones actuales mientras el genérico no alcanza paridad.

**Fase C:** score con exploración controlada y cadencias dinámicas en modo sombra; comparar cobertura, novedades corroboradas, costo, eventos omitidos, estabilidad y sesgos por disciplina frente al Radar actual durante varios ciclos ordinarios; rollback sencillo por política versionada.

**Fase D:** activar paulatinamente solo los subgrupos que mejoren; la admisión a `public.radar_agenda_events`, modificaciones de entidades y publicación web siguen fuera de las facultades del ejecutor.

**QA mínimo verificable:** nueva fuente sin código de dominio, fuente que cambia de HTML a feed, fuente que no publica eventos fechados, fuente JS, fuente secundaria que corrobora otra, dos horarios de misma obra, 429, fuente con muchos duplicados, fuente rara relevante (yoga/cerámica/vinos), y reversión ante caída de cobertura. Exigir trazabilidad por decisión y conservar datos anteriores. Evaluar sobre páginas concretas y evidencia real, no sólo tests sintéticos.

## 8. Qué NO hacer
- No crecer el número de `if host == ...` por cada nuevo lugar salvo excepción acotada con test y retiro previsto.
- No penalizar una institución por no anunciar eventos: su valor como entidad puede ser alto.
- No usar el éxito de GitHub, HTTP 200, cantidad de URLs, `index_only` o cantidad de duplicados como indicador suficiente de cobertura cultural.
- No fusionar sesiones diferentes, no inferir horarios ni fechas, no publicar automáticamente, no cambiar la protección de Neon/Vercel ni crear tareas duplicadas.
- No desmantelar los adaptadores existentes antes de probar una estrategia universal capaz de reemplazarlos con paridad.
