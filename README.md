# Por Acá · Explorador cultural

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

**No** se descubrieron eventos nuevos verificados ni se hizo escritura en Neon. [Informe completo](docs/RESULTADO_PRUEBA_INSTAGRAM_20261028.md).

**Límites explícitos:** no hay cron, no hay secrets, no se escriben datos en Neon, no se toca el Radar original ni se publican hechos. Recibir HTML de Instagram **no equivale** a haber leído sus publicaciones.

Documentación: [alcance, metodología y etapas siguientes](docs/EXPERIMENTO.md).

Código: [src/explore.py](src/explore.py) · [pruebas](tests/test_explore.py) · [workflow](.github/workflows/probar-fuentes.yml).
