# Por Acá — frontera semántica de Radar → Neon → web · 29/10/2026

**Decisión operativa:** Radar captura pistas y sesiones, NO define la identidad cultural definitiva. El campo `radar_definitivo.event_occurrences.category` es **pista nullable** y no está aprobado automáticamente como categoría de la agenda pública.

## Distinciones

1. `entity_kind` / identidad física: estudio fotográfico, cooperativa y predio, teatro municipal, programa experimental, colectivo, sala, etc. No deducirla de una función.
2. `primaryTopic`: especialidad editorial de una identidad (cerámica, yoga, teatro, música, danza...). No equivale a todas sus actividades ni a los géneros de los eventos alojados.
3. `event.discipline`: disciplina sustentada por el anuncio original, NO heredada de la sede.
4. `event.format`: recital, festival, taller, feria, obra, etc., independiente de disciplina.
5. `spatial relation`: `inside` / `based_at` con evidencia y control de visibilidad, jamás `organized_by` por compartir inmueble.
6. `source` / `observation` / `canonical event`: niveles diferentes con puertas editoriales.

## Corrección mínima de nombres en nueva adquisición
- El parser deja de emitir `arte` (legado) y propone `artes` cuando el título nombra muestra, exposición o galería.
- Deja de emitir `formacion` como supuesta disciplina. Cuando el título dice **cerámica** o **yoga**, devuelve la disciplina explícita. **Taller/curso/clase** por sí solos no permiten inferir un tema; se quedan en `NULL` y posteriormente el formato se analiza por separado.
- Una noticia o convocatoria genérica sin materia reconocible pasa a `NULL`, no a `comunidad`. Comunidad es identidad/propósito, no la categoría residual por falta de evidencia.
- No se reinterpretan ni modifican las 33 ocurrencias, 465 registros de cartelera, 220 candidatos ni eventos previamente almacenados. Un cambio de clase retrospectivo requiere nueva evidencia, auditoría y contrato de aceptación, nunca migración masiva.

## Puertas de entrada
- `radar_definitivo` sigue recibiendo **datos no verificados** desde GitHub Actions.
- El gate `radar_definitivo.motor_ingest_gate_v1` no exige una clasificación automática para autorizar eventos: sigue bloqueando por fuente, horario, sede, función y evidencia. **0 autorizados a escritura en el corte 29/10.**
- No se habilita escritura a `public.radar_agenda_events` ni se promueven entidades por esta corrección.
- No se agregan ejecutores ni programaciones; el workflow `radar-definitivo-ci.yml` solo valida el código. El disparo cultural de 05/13/21 horas mantiene su comportamiento.

**Enlace de referencia:** contrato central `data/semantic-boundary-contract-v1.json` en `diegomontenegroext-hash/poraca-lp`; fuente de verdad de publicación, mientras este programa conserva únicamente heurísticas de adquisición.
