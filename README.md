# Por Acá · Explorador cultural

## Radar Definitivo — adquisición principal de Por Acá

**Operación al 28/10/2026:** la tarea ChatGPT recolectora anterior está **pausada**. Una sola tarea **«Por Acá — Radar GitHub 3 veces al día»** actúa como programador GPT **05:00 FULL, 13:00 incremental y 21:00 incremental ART**. Hace `GitHub.fetch_file/update_file` sobre `ops/radar-fallback-trigger.txt` y el workflow [Radar Definitivo](.github/workflows/radar-definitivo.yml) ejecuta el programa. No hay `schedule` directo de GitHub porque ningún disparo horario fue confirmado en las primeras pruebas.

**Integración comprobada:** prueba `incremental` disparada por commit [GitHub #40682506769](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40682506769), `SUCCESS`; `neondb.radar_definitivo.runs` registró `mode=incremental`, `target=operational_neondb_staging` y 0 fuentes vencidas a esa hora. Las próximas pruebas reales del programador son las 13:00/21:00 ART. 13 fuentes prioritarias accesibles tienen ahora cadencia 7 h; el resto mantiene sus umbrales.

[Plan de estabilización (prioridad actual)](docs/PLAN_ESTABILIZACION_RADAR_20261028.md) · [Contrato de datos y aislamiento](docs/RADAR_DEFINITIVO_20261028.md) · [Programa](src/radar_definitivo.py) · [Pruebas](tests/test_radar_definitivo.py).

**Fase actual: paridad de agendas, no ampliar a ciegas.** `public.radar_agenda_events` tiene 159 registros, 51 con fecha desde el 28/10. La comparación inicial estricta `radar_definitivo.agenda_baseline_coverage_v1` registra 0 coincidencias fecha+título, 1 URL recuperada sin coincidencia y 50 no recuperadas: brecha de extracción/comparación a resolver con adaptadores específicos de Genda, Alternativa Teatral, teatros y agendas; no afirmar ausencia de esos 50 eventos. La última FULL recuperó 27 fuentes, dejó 29 páginas `index_only` y 7 errores.

**Inventario y destino:** 225 fuentes catalogadas, 63 webs activas, 39 en revisión y 123 perfiles IG como inventario de descubrimiento indirecto. Escritura **operativa** en DB `neondb`, esquema aislado `radar_definitivo`, mediante secreto dedicado `NEON_RADAR_OPERATIONAL_DATABASE_URL` ya probado. Candidatos/ocurrencias/entidades permanecen **no verificados**: ningún evento se publica sin Motor y control editorial. Límites: 360 HTTP, 24 min de adquisición, hasta 24 posts IG exactos con 4 s entre accesos y parada al recibir 429.

---

## Nuevo: Radar paralelo 0.1 · base Neon aislada

**Ya instalados:** programa `src/radar_parallel.py`, pruebas, [workflow Radar paralelo](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/workflows/radar-paralelo.yml) y base independiente `poraca_explorador` con 15 fuentes activas. El Radar original de ChatGPT sigue intacto.

**Estado histórico: piloto archivado, sólo ejecución manual.** Primera escritura real a Neon verificada el 28/10: [run #40627651136](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40627651136), **6 fuentes consultadas, 5 accesibles, 6 candidatos nuevos y 6 controles guardados**. Los horarios que tuvo ese piloto fueron retirados al pasar a Radar Definitivo. [Contrato operativo y consultas de verificación](docs/RADAR_PARALELO_OPERACION.md).

**Bootstrap histórico del piloto:** se había previsto una ejecución excepcional para 00:50 ART, pero no se observó un disparo por horario de GitHub. El piloto dejó de tener programación automática.


Los datos nuevos se guardarán siempre como `candidates.review_state='unverified'`: no se publican automáticamente ni se confunden con hechos aceptados.

---

Experimento de adquisición cultural de La Plata, gratuito, autónomo y separado del proyecto privado **Por Acá**.

**Estado:** tres pruebas read-only completadas: webs, permalinks exactos y descubrimiento de enlaces desde agendas. Aún no es un Radar completo. Nueve fuentes (6 webs / 3 perfiles Instagram); intenta leer HTML y registrar pistas **no verificadas**.

## [Ejecutar la prueba en Actions](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/workflows/probar-fuentes.yml)

1. En la pestaña Actions, abrir **Por Acá - prueba de fuentes**.
2. Elegir **Run workflow**, rama main.
3. Abrir el Summary y el log de **Probar nueve fuentes publicas**.

Pruebas verificadas:
- [Perfiles públicos: 3/3 HTTP 429; webs 5/6 abiertas](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40624913514).
- [Tres permalinks exactos históricos: 3/3 HTTP 200 con metadatos de post](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40625398760).
- [Agenda pública → 6 permalinks detectados → primer post abierto HTTP 200](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40625709193).

**No** se confirmaron eventos nuevos en estas pruebas; la primera escritura a Neon ya está comprobada, con candidatos `unverified`. [Informe de Instagram](docs/RESULTADO_PRUEBA_INSTAGRAM_20261028.md).

**Límites explícitos de las pruebas originales:** fueron manuales, sin secretos ni Neon. **El Radar paralelo actual sí tiene cron y secreto cifrado**, escribe exclusivamente en la base experimental. No se toca el Radar original ni se publican hechos. Recibir HTML de Instagram **no equivale** a haber leído sus publicaciones.

Documentación: [alcance, metodología y etapas siguientes](docs/EXPERIMENTO.md).

Código: [src/explore.py](src/explore.py) · [pruebas](tests/test_explore.py) · [workflow](.github/workflows/probar-fuentes.yml).
