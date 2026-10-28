# Prueba 1 · GitHub Actions pública · 28/10/2026

- Workflow: [run 40624913514](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40624913514), push inicial, concluido SUCCESS.
- Código: commit `2c3089c5cfccda30df052d708ba79c21745e41ab`.
- Tests: PASS. Programa Python ejecutado hasta el final.
- Alcance: nueve fuentes consultadas sin credenciales, sin cron, sin DB Neon, sin cambios en Radar ChatGPT.

## Resultado HTTP de la prueba

| Fuente | Resultado |
|---|---|
| Casa Metro | HTTP 200; título y enlaces de cartelera/eventos extraídos sin validar |
| La Plata Tango | HTTP 200; HTML truncado a 400 KiB, enlaces generales sin validar |
| Alpedó | HTTP 200; enlaces por fecha |
| 0221 / Qué Hago | HTTP 200; títulos de artículos y enlaces de agenda |
| Genda / Agenda La Plata | HTTP 200; secciones y rutas por fecha |
| Centro de Arte UNLP | Error URL/red, sin código HTTP útil; causa exacta pendiente |
| Instagram cine Select | HTTP 429, acceso restringido |
| Instagram EcoSelect | HTTP 429, acceso restringido |
| Instagram Casa52 | HTTP 429, acceso restringido |

**Lectura honesta:** 5 de 6 webs respondieron HTML utilizable; 3 de 3 perfiles de Instagram fueron limitados por HTTP 429. Ningún post de Instagram se leyó; ninguna sesión cultural se validó o aceptó. No confundir links genéricos de navegación ni notas de prensa con novedades originales.

## Criterio siguiente
1. Agregar extracción específica de enlaces de eventos y detalles en las webs accesibles, con prueba de fecha/hora/organizador en página individual.
2. Registrar fallos y reintentos cuidadosos, sin insistir en perfiles limitados por 429 ni intentar evadir sus controles.
3. Contrastar candidatos de un lote con Neon en modalidad read-only, conservando fuentes, URL y fecha. Sólo entonces discutir escritura de candidatos por un contrato de mínima autoridad, nunca aceptación automática.
4. Ampliar fuentes oficiales sociales *alternativas* (sitios de las entidades, newsletters, agendas, plataformas de entradas) para cubrir huecos de Instagram. Un HTTP 429 no prueba que no haya nuevas publicaciones.
5. No activar programación ni cambiar la tarea cultural existente hasta demostrar rendimiento de extracción y deduplicación.

**La prueba acredita independencia del runtime de GitHub, no la cobertura real de la ciudad.**
