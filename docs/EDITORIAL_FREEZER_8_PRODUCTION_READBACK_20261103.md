# Por Acá — Freezer Festival 2026 · ocho originales admitidos en un lote

**Corte:** 03/11/2026. **Carácter:** certificación de admisión editorial e integridad Neon; **no** acredita participación ni realización efectiva de actividades.

## Qué se hizo y evidencia
- [Programa del festival, fuente original](https://festival.freezer.com.ar/2026/programacion/), fechas individuales y horarios de inicio anunciados (5, 12, 14 y 15/11). No se convirtieron rangos de exhibición `10 a 18` ni espacios sin dirección en funciones de inicio inventado.
- Radar: fuente original `rd-official-freezer-2026` y editorial `src-freezer-festival-2026-original` (rol `institutional_program`). **No** se agregó cron, parser por sede ni fuente espejo.
- Neon producción `frosty-union-52906378 / br-mute-recipe-b4odj2bl`: ocho observaciones deterministas `obs-freezer-2026-*` con `source_event_url` individual (fragmento por día), fecha, horario y `originalVenueWithRoom`; primero se probaron ocho inserciones en QA y se verificó coincidencia exacta de original/identidad por ocho SELECTs.
- Aprobación **por escritor preexistente** `public.poraca_apply_cultural_batch_v1`, ejecución `cultural-freezer-official-review-20261103-8`, batch `freezer-8-originals-20261103`. Recibo transaccional: **changes=8, held=0, duplicates=0**, ocho `ACCEPTED_EVENT`. **No** se insertaron canónicos por SQL directo.
- Readback independiente: ocho `matched_event_key` que existen en `radar_agenda_events`, ocho `verification=confirmed`, ocho `hosted_at accepted`, evidencia `fieldEvidence` con nombre de sede, parent id y `room=Auditorio` para las seis actividades de sala. 19 futuros confirmados en total, **5 categorías** (antes: 11). Dos propuestas anteriores `El Ánimo` siguen en revisión sin publicar.
- La API usa `poraca_motor_qa` limitada a SELECT de rama operacional; ejecutamos su `eventsSQL` exacto con ese rol: **148 filas del feed (incluye archivo), ocho Freezer nuevos y 19 confirmados futuros**.
- UI web `fb6cd953bcca39fe3c6768c274e0738feae382ae`: [QA visual #41704787114 SUCCESS](https://github.com/diegomontenegroext-hash/poraca-lp/actions/runs/41704787114); los detalles de sala solo se muestran cuando hay prueba exacta de fuente primaria+fecha+hora+venueId. La misma ubicación se conserva en modal, tarjeta, WhatsApp y calendario. Casos negativos en test rechazan sala forjada, hora discordante y entidad errónea.
- Vercel `poraca-lp-privado` publicación **única** `dpl_DKPFbqBmYdvSRWQcxbfrmFM9bRbM`, `production READY`, commit exacto `fb6cd953`, protección **SSO ON**. No deshabilitar SSO por test.

## Detalle de los ocho hechos

| Fecha ART | Hora | Actividad | Sede parent | Sala/sector probado |
|---|---|---|---|---|
| 05/11 | 17:00 | Freezer · Inauguración de Exposiciones | Pasaje Dardo Rocha | Pasaje Dardo Rocha |
| 12/11 | 20:30 | Freezer · Programa de Proyectos Fotográficos 2026 | Casa 62 | Casa 62 |
| 14/11 | 14:30 | Freezer · Ausencias | Centro de Arte UNLP | Auditorio |
| 14/11 | 16:30 | Freezer · Reapropiaciones fotográficas y memoria viva a 50 años del Golpe | Centro de Arte UNLP | Auditorio |
| 14/11 | 19:00 | Freezer · Guardia de Cenizas | Centro de Arte UNLP | Auditorio |
| 15/11 | 15:00 | Freezer · Disparos, imágenes y representaciones en la Argentina de hoy: a 50 años del Golpe | Centro de Arte UNLP | Auditorio |
| 15/11 | 16:30 | Freezer · La fotografía es | Centro de Arte UNLP | Auditorio |
| 15/11 | 18:00 | Freezer · Carne de Cañón | Centro de Arte UNLP | Auditorio |

Cada función tiene un ID canónico distinto, un recibo con `observationId`, un vínculo a la sede y el enlace por día del organizador. El programa es gratuito en varias fechas, pero **no se infieren cupos ni duración**.

## Qué NO quedó acreditado
- A2 requiere >=30 eventos futuros originales: **19/30**; A3 requiere >=8 categorías: **5/8**. A4 y P4 tampoco se cumplen por ocho actividades de un mismo festival y fuente. IICS v1 permanece **5,2/10** (26/50 PASS).
- La prueba HTTP de navegador **autenticado en producción** del nuevo deployment todavía no se ejecutó en este corte: hay build READY, QA Chromium del SHA en Actions y lectura del SQL exacto de la API con rol restringido, que son evidencias distintas.
- F4 no cambia: ocho funciones del mismo sitio NO son ocho fuentes independientes. O3 y F5 requieren FULL naturales y prueba real de recuperación. Biblioteca Pública UNLP aún no dispone de primer `source_check`.

## Próximo lote de mayor impacto
1. Unificar 8 casos de **Casa Metro** por sala, después investigar Doble-T (8 por dirección sola) y Teatro Metro (11 interno, **distinto** de Casa Metro). No promocionar identidades internas sin revisión.
2. Completar muestras independientes **E4** sobre los mismos 30 IDs; no reemplazar casos no accesibles.
3. Mejorar circuitos con menos oferta **vino, literatura, talleres y deportes**, manteniendo la distinción entre `práctica habitual` y `evento futuro`; P4 12 vías efectivas con originales.
4. Mantener una QA consolidada por lote, sin despliegues o branches por una sola ficha.

**Responsables:** [#10 Editorial](https://github.com/diegomontenegroext-hash/poraca-lp/issues/10), [#35 Atlas](https://github.com/diegomontenegroext-hash/poraca-lp/issues/35), [#30 UX](https://github.com/diegomontenegroext-hash/poraca-lp/issues/30), [#16 gobierno](https://github.com/diegomontenegroext-hash/poraca-lp/issues/16).
