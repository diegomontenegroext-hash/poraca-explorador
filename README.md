# Por Acá · Explorador cultural

## Radar Definitivo — nuevo motor experimental autónomo

**Implementado el 28/10/2026:** segundo motor independiente dentro de este mismo repositorio, con [workflow Radar Definitivo](.github/workflows/radar-definitivo.yml), [código](src/radar_definitivo.py), [pruebas](tests/test_radar_definitivo.py) y [contrato completo](docs/RADAR_DEFINITIVO_20261028.md).

- **225 fuentes catalogadas en Neon experimental:** 63 webs habilitadas para lectura, 39 webs históricas en revisión y 123 perfiles culturales de Instagram como inventario de descubrimiento (NO scrapeo directo de feeds).
- **Esquema Neon exclusivo:** `poraca_explorador.radar_definitivo`, con tablas independientes para fuentes, corridas, controles, candidatos, corroboraciones y entidades culturales tentativas.
- **Primer disparo autónomo:** `push` de la creación del workflow; arranca modo `full` automáticamente; [consultar ejecución inicial](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40630215172). No declarar éxito hasta que finalice.
- **Después:** seguimiento incremental 3 veces al día (07:27, 15:27, 23:27 ART), y un barrido `full` semanal (domingo 02:42 ART). Los horarios son solicitudes al programador de GitHub, que puede retrasarlos.
- **Límite:** 36 webs por corrida, hasta 8 enlaces por web en full, hasta 4 en incremental, 200 peticiones totales, 19 minutos internos y 30 minutos de workflow, parada por 429.
- **Sin promoción automática:** cada candidato queda sin verificar; no altera la web, la API, la Neon operativa ni los otros dos radares.

---

## Nuevo: Radar paralelo 0.1 · base Neon aislada

**Ya instalados:** programa `src/radar_parallel.py`, pruebas, [workflow Radar paralelo](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/workflows/radar-paralelo.yml) y base independiente `poraca_explorador` con 15 fuentes activas. El Radar original de ChatGPT sigue intacto.

**Estado de puesta en marcha: funcionando en modo paralelo.** Primera escritura real a Neon verificada el 28/10: [run #40627651136](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40627651136), **6 fuentes consultadas, 5 accesibles, 6 candidatos nuevos y 6 controles guardados**. Se programaron tres corridas diarias a las 10:20, 16:20 y 22:20 ART; GitHub puede retrasar los disparos. [Contrato operativo y consultas de verificación](docs/RADAR_PARALELO_OPERACION.md).

**Bootstrap amplio:** corrida automática excepcional programada para **28/10/2026, 00:50 ART**, con [cron controlado por fecha](.github/workflows/radar-paralelo.yml) y modo `full` (15 fuentes, hasta nueve detalles por fuente). Puede empezar tarde por la cola de GitHub. Luego siguen las tres corridas habituales de 10:20, 16:20 y 22:20 ART, en modo `incremental`, con fuentes vencidas y deduplicación por URL. [QA del barrido ampliado](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40628415819) pasó. La ejecución full programada **todavía no se ha confirmado como ocurrida**.

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
