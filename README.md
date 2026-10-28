# Por Acá · Explorador cultural

Experimento de adquisición cultural de La Plata, gratuito, autónomo y separado del proyecto privado **Por Acá**.

**Estado:** prueba manual de conectividad, no Radar completo. Nueve fuentes (6 webs / 3 perfiles Instagram); intenta leer HTML y registrar pistas **no verificadas**.

## [Ejecutar la prueba en Actions](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/workflows/probar-fuentes.yml)

1. En la pestaña Actions, abrir **Por Acá - prueba de fuentes**.
2. Elegir **Run workflow**, rama main.
3. Abrir el Summary y el log de **Probar nueve fuentes publicas**.

La primera validación se disparó también al incorporar el workflow mediante push. El resultado real estará en [Actions](https://github.com/diegomontenegroext-hash/poraca-explorador/actions).

**Límites explícitos:** no hay cron, no hay secrets, no se escriben datos en Neon, no se toca el Radar original ni se publican hechos. Recibir HTML de Instagram **no equivale** a haber leído sus publicaciones.

Documentación: [alcance, metodología y etapas siguientes](docs/EXPERIMENTO.md).

Código: [src/explore.py](src/explore.py) · [pruebas](tests/test_explore.py) · [workflow](.github/workflows/probar-fuentes.yml).
