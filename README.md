# Por Acá · Explorador cultural

## Nuevo: Radar paralelo 0.1 · base Neon aislada

**Ya instalados:** programa `src/radar_parallel.py`, pruebas, [workflow Radar paralelo](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/workflows/radar-paralelo.yml) y base independiente `poraca_explorador` con 13 fuentes. El Radar original de ChatGPT sigue intacto.

**Estado de puesta en marcha: funcionando en modo paralelo.** Primera escritura real a Neon verificada el 28/10: [run #40627651136](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40627651136), **6 fuentes consultadas, 5 accesibles, 6 candidatos nuevos y 6 controles guardados**. Se programaron tres corridas diarias a las 10:20, 16:20 y 22:20 ART; GitHub puede retrasar los disparos. [Contrato operativo y consultas de verificación](docs/RADAR_PARALELO_OPERACION.md).

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
