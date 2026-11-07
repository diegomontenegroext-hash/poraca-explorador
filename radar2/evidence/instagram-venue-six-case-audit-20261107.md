# Radar 2 — diagnóstico real de sedes faltantes en Instagram

**Fecha:** 07/11/2026 ART. **Alcance:** lectura y pruebas aisladas; **sin cambios** en captación, parser, Neon, Vercel, crons ni agenda aprobada.

## Corte y prueba

Sobre `radar2.private_discoveries`, origen Instagram, eventos/programas fechados del **07/11 al 22/11** inclusive, excluidos históricos:

- 68 propuestas, 45 con `venue = NULL`, 33 con `event_time = NULL`, 22 sin ambos.
- **45/45 registros sin sede conservan `evidence.origin_account`**.
- 39/45 corresponden a `caption-v2.3` (`source_observed`); 6/45 a `compound-v1` (`curator`, Luti).
- Un cruce **exacto y no difuso** entre `origin_account` y el usuario Instagram de `official_url` de entidades `venue/approved_public` detectó **12 registros sin sede con cuenta vinculada a una sede aprobada**: Pura Vida 5, Cineclub Proyecciones Terrestres 3, Teatro UNLP 2, Museo de Arte y Memoria 1, Patio Café City Bell 1. **12 vínculos posibles, no 12 eventos validados ni 12 sedes para asignar automáticamente**.
- Corrida aislada en sandbox sobre **8 publicaciones originales** recuperadas de `radar2.documents`, utilizando `caption.interpret` vigente en `main` y `accounts.json`: **0 publicaciones recuperaron sede**. Esto demuestra defecto vigente de parseo/conciliación; no solamente datos anteriores sin replay.

## Seis casos y un control negativo

| Caso | Publicación/fecha | Hecho contrastable en original | Cruce independiente / catálogo | Causa y tratamiento |
|---|---|---|---|---|
| **Teatro UNLP · La Nona** | [Anuncio 7/11 21:00](https://www.instagram.com/p/DfVTxkaP0Nz/) + [reel de aniversario](https://www.instagram.com/reel/DfawlZ3PWs5/) | El anuncio contiene **Teatro UNLP**, dirección 10 entre 54 y 55; el otro omite la sala pero viene de la misma cuenta | `public.poraca_knowledge_entities`: `teatro-unlp` aprobado con `official_url=https://www.instagram.com/teatrounlp/`. La misma función está en El Día y TeatroCerca | Parser busca `📍`, no `📌`, y el catálogo corto `accounts.json` no incluye @teatrounlp. Resolver en el anuncio literal; enlazar el reel por función/fecha y entidad, sin nueva alta |
| **Centro de Arte UNLP · Josefina Ignisci** | [7/11 20:00](https://www.instagram.com/p/DfP6oY1Kr9E/) | Menciona **auditorio del centrodearteunlp** | Entidad `centro-arte` aprobada; `accounts.json` contiene `Centro de Arte UNLP`; Genda anuncia la misma artista, día/hora en Edificio Karakachoff | Coincidencia por texto normalizado exige espacios; el handle aparece concatenado. Incorporar alias controlado cuenta↔sede y cruce de mismo espectáculo |
| **Taller Laura Gan · fotocerámica** | [8/11 13:00](https://www.instagram.com/reel/DfDPZVXCGX6/) | Nombre **Taller Laura Gan** y dirección **Av. 13 n.º 343, La Plata** | Entidad `laura-gan-taller` aprobada; otras publicaciones de la misma cuenta sí recuperaron la sede | Regex de sala explícita exige prefijo `en ` o marcador `📍`; el nombre aparece en línea informativa independiente. Admitir prueba literal con dirección y segmentación |
| **Teatro Espacio 44 · Yuna soy yo** | [7/11 18:00](https://www.instagram.com/reel/DezXjlTxAvM/) | Perfil del espacio; hashtag relacionado; URL de obra en Alternativa Teatral | El Día anuncia mismo título, día, hora, **Teatro Espacio 44**. Entidad `research-espacio-44-laplata` está **verified_internal**, aún no `approved_public` | La cuenta no figura en `accounts.json`; no adjudicar identidad pública automáticamente. Propuesta de match con prueba cruzada editorial y estado de venue provisional |
| **Pura Vida · agenda semanal** | [Programa 4–8/11](https://www.instagram.com/p/DfVQPF5zxH1/) | Programación por jornadas y artistas, sin nombre literal de la sala en cada tramo. Medianoche con posible ambigüedad de día civil | Entidad `pura-vida` aprobada y `official_url` coincide exactamente con @puravidalaplata2008 | 5 propuestas futuras sin sede en ventana; el parser produce títulos genéricos repetidos **AGENDA SEMANAL** y medianoches sin resolver. **Primero segmentar por día/actividad**, luego vincular a sede solo cuando no exista señal de actuación fuera de ella |
| **Cineclub Proyecciones Terrestres · tres películas** | [Programa 7/11](https://www.instagram.com/p/DfartNwlwom/) | Tres funciones, una a medianoche, con **dirección calle 3 entre 66 y 67 n.º 1663** y referencia a una sala | Entidad `cineclub-proyecciones` aprobada y `official_url` igual a @proyeccionesterrestres | El intérprete descarta direcciones puras de `📍` como nombres de sede (decisión razonable), pero no resuelve esa dirección contra el perfil/catálogo. Guardar dirección como evidencia; candidato de sede únicamente tras match del organizador/catálogo y hora/día por función |

**Control negativo esencial:** [@sindicatoargentinodeboleros](https://www.instagram.com/p/DfZ85DXo7pe/) publica un itinerario con **varias ciudades y lugares**, además de transmisiones por TV y YouTube. Una cuenta de artista u organizador **jamás** debe imponer sede a todos sus anuncios. Además quedaron títulos pobres como «por Canal 7». El sistema debe clasificar evento presencial/transmisión/lanzamiento y segmentar antes de cruzar identidades.

## Causas técnicas comprobadas

1. En `radar2/caption.py` (versión `caption-v2.3`) la búsqueda inicial de sede usa nombres de `accounts.json` **dentro del texto**, no un registro tipado cuenta↔sede. El archivo tiene ~20 cuentas, el roster ampliado ~123, pero este roster clasifica `organizador` incluso a algunas salas. No usar `kind='organizador'` para inferir `venue`.
2. El fallback de nombres exige `en ` o `📍`; no contempla `📌 Teatro UNLP`, sedes en líneas independientes ni handles concatenados. `📍 Calle ...` no prueba por sí solo un nombre de establecimiento.
3. `caption-v2.3` no enlaza eventos con `public.poraca_knowledge_entities` ni con otras fuentes por **obra+fecha+función+sede verificada**. Hay cruces positivos disponibles para La Nona, Yuna soy yo y Josefina Ignisci.
4. Programas multiparte (Pura Vida), publicaciones curadas (Luti) y anuncios itinerantes (Sindicato) requieren segmentar y diferenciar roles. No hacer un fallback universal «sede = nombre de cuenta».

## Intervención correcta para el siguiente lote (sin nueva arquitectura)

- Añadir **resolución conservadora de lugar** al intérprete existente, usando catálogo de identidades/alias aprobado y evidencia literal de cada anuncio. Orden: **sede explícita en segmento → relación venue↔cuenta previamente validada sin señal de traslado → corroboración entre fuentes del mismo acto y fecha → pendiente**. Registrar `venue_basis`, `venue_evidence`, `venue_entity_candidate` y abstenciones. Nunca heredar nombre de sala de un organizador itinerante.
- Diferenciar **título del evento / nombre de programa / artista / función** y **presencial / online / lanzamiento / retrospectiva**, manteniendo fechas y medianoches conservadoras.
- Probar sobre este holdout de seis casos + control itinerante, además de casos negativos de artista/curador y posts fuera de sede. **No entrenar un umbral contra el mismo holdout y certificarlo como independiente**; medir después una muestra ciega adicional de ≥20 publicaciones.
- Replay de los **originales ya conservados**, sobre los mismos IDs, con diff exacto de campos, guardas, preservación de versiones, ensayo de idempotencia y readback; NO resetear Neon, NO nuevas consultas Instagram innecesarias, NO aprobar en la agenda pública por completar venue.
- Medir sobre el lote de 45: sedes explícitas confirmadas, sedes vinculadas con identidad validada, casos con cruce independiente, ambiguos legítimos y **falsos positivos de vinculación**. La meta no es llenar 45/45, sino elevar la recuperación segura sin inventar sedes.

**Conclusión:** falla real de extracción y aprovechamiento de memoria cultural; API Meta adquirió los originales. No atribuirla solo a la fuente externa. Este documento es evidencia para corregir, **no una certificación de recuperación ya lograda**.
