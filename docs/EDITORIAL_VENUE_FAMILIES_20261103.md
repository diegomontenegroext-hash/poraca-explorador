# Por Acá — familias de sedes, habilitación editorial sin autoaprobación
**Corte:** 03/11/2026 · **Estado:** consulta SQL real sobre Neon producción, solo lectura. **IICS permanece 5,2/10.**

## Por qué importa
Una única actividad puede estar en `HOLD_APPROVED_VENUE_MAPPING` porque el original nombra una sala dentro de un edificio aprobado; una coincidencia parcial de texto no es autorización de publicación. También existe el caso inverso: `Teatro Metro La Plata` tiene identidad **interna** diferente a `Casa Metro` **pública**. La revisión debe devolver entidades candidatas y conservar siempre el texto íntegro de sala y la URL original.

## Cohorte efectiva
La consulta [SQL read-only](../sql/20261103_venue_family_review_READ_ONLY.sql) evalúa **47 propuestas** del embudo abierto. Clasificación:
- **19 `REVIEW_PARENT_AND_SUBSPACE`**: 11 del festival Freezer con candidatos parentales `centro-arte`, `casa-62`, `pasaje-dardo-rocha`; otras 8 del catálogo Casa Metro con `casa-metro`. Se mantiene HOLD hasta revisión individual de fuente y sala.
- **12 `HOLD_PARENT_INTERNAL`**: 11 carteleras `Teatro Metro La Plata` y 1 `Viejo Almacén El Obrero` con identidad `verified_internal`. No equiparar Teatro Metro y Casa Metro.
- **16 `HOLD_NO_REVIEWABLE_PARENT`**: 8 Freezer con sedes sin entidad parent segura, y 8 entradas de Doble-T que publican solo `C. 23 565`, dirección que NO prueba identidad.

**Fuente original Freezer:** [programa 2026](https://festival.freezer.com.ar/2026/programacion/) (5–17/11). El programa distingue Centro de Arte, Auditorio, Sala A, Espacio Dickinson, otros locales, franjas horarias y actividades con inscripción. La consulta NO considera estas coincidencias como verdad editorial; conserva la subsede original.

## Entrega por bloque (no por ficha)
1. Resolver `centro-arte` + salas; `casa-62`, `pasaje-dardo-rocha` y `casa-metro` como cuatro **familias** con documentos originales independientes y sala conservada. La recomendación de parent por SQL es un índice de revisión.
2. Auditar Teatro Metro separado, sin promoción de `verified_internal` sin aprobación legítima; confirmar Doble-T por nombre a partir del original, no solo dirección.
3. Solo con la verificación individual `evento→fecha/hora real→sede/subsede→fuente→autoridad editorial`, pasar una cohorte a observaciones retenidas. Canonizar exclusivamente casos explícitamente aprobados y comprobar API/web tras QA por release.
4. Medir resultados de cohorte: `revisión iniciada`, `evidencia comprobada`, `HOLD justificado`, `observación segura`, `canónico aprobado`, `API visible`. Nunca utilizar los 19 como eventos publicados o +0,2 del IICS.

No se cambian fuentes, Neon, roles, estado editorial ni Vercel con esta consulta. La implementación no genera nuevas acciones de Radar. Un QA de código consolidado verifica el contrato estático.
