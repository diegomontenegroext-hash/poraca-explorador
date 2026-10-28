# Por Acá — Tanda 4: originales, sedes y brechas de agendas (28/10/2026)

**Objetivo:** reducir el gap medible en la baseline sin traer datos heredados como si fueran nuevas captaciones y sin escribir a las tablas públicas.

## Cambios y verificaciones

1. **Alternativa Teatral — corrección por evidencia original.** En `src/radar_agenda_adapters.py`, el extractor de obra ahora lee el nombre de sala impreso antes de la dirección y dispone de fallback restringido para HTML aplanado. Detecta sesiones con día/hora/fecha explícitos aunque no haya etiqueta «Entrada». Para `Hasta el ...` **no expande recurrencias**: solo toma los días escritos y valida que coincidan con el nombre del día de semana. Se evita registrar dos veces la misma sesión cuando la ficha repite el horario con y sin «Entrada».
2. **Watchlist según brecha real.** En `src/radar_definitivo.py`, se prioriza el documento original con sede por resolver, seguido de eventos no recuperados, manteniendo URL original y efectuando descarga real. El listado heredado **no crea** funciones por sí mismo. Esto evita gastar las primeras solicitudes por fuente en eventos que ya están completos.
3. **Pruebas de regresión** con las fichas reales de Teatro Estudio, Espacio 44, Escenario 40 y En Eso Estamos; validación de que no se infieren viernes intermedios. Suite QA de GitHub [#40705719911](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40705719911) **SUCCESS**. Se corrigieron fallos intermedios de tests anteriores a esa ejecución; no ocultarlos.
4. **Readback real.** [Incremental #40705220964](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40705220964) incorporó *Epifanía*, viernes 30/10 a las 21:30, con sede aún no identificada. [Incremental #40706384507](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40706384507) incorporó **4 evidencias originales con sala**: *Epifanía* / Escenario 40, *Volcada* / Espacio 44, *Cuadriláteros 6* y *La gravedad de lo incierto* / Teatro Estudio de las Artes. Se conservan las filas antiguas sin sede para trazabilidad; el reporte de paridad favorece ahora el registro completo sobre su versión vieja.

## Nueva medición verificable de baseline fija (51 eventos)

- **21** coincidencias completas por URL original, fecha y hora y con nombre de sede.
- **2** conflictos de hora en HOLD (Carmen Sánchez Viamonte y Benjamín Amadeo): Livepass muestra 20:00 para ambos, frente al registro previo de 21:00 y 20:30, respectivamente. No alterar agenda aceptada sin validación y aceptación de cambio de horario.
- **28** sin recuperación por la regla de cotejo estricta. Aproximadamente 11 provienen de enlaces Instagram; el resto de originales de teatros, agendas culturales, páginas de organizaciones, sitio de Feria EDITA, etc. El conteo de pendientes NO representa eventos inexistentes ni obliga a inventar equivalencias.

La vista operativa `radar_definitivo.baseline_event_parity_checked_v3` y el resumen `radar_definitivo.event_chain_readiness_v1` reflejan la mejora inmediatamente. Las verificaciones han permanecido en staging, nunca en `public.radar_agenda_events` ni `public.radar_v3_source_observations`.

## EDITA y prioridades restantes

- **Feria EDITA 2026:** su propia web anuncia expresamente 5 y 6 de diciembre y `#EDITA2026`, sin horas de comienzo. El extractor ahora admite dos registros con **`event_time=NULL`**, categoría documental / programa oficial, para revisión posterior. QA [#40707320107](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40707320107) **SUCCESS**. **Todavía no consta su lectura de producción** en una corrida iniciada tras estos commits; no afirmar que ya están guardados en Neon.
- **Teatro Metro:** verificar lectura efectiva de *Pequeño Pez* 01/11 17:00 y *Nico de Tracy / Purga* 05/11 21:00, ambos con fecha/hora visible en su ficha de entradas; no copiar la baseline.
- **Alternativa restante:** *El Ánimo* presenta fechas 01/11, 06/11 y 27/11 según su original; **no forzar** coincidencia con una ficha de 30/10 si la fuente no la publica. *Escrito en la piel*, *Fakeland S.A.*, *Muerde* y *Las del Lirio* requieren elegir sede y función del día correcto cuando la obra informa dos recintos.
- **Lumen Artis / Achmed:** el relato principal inspeccionado no aportó horario explícito; mantener HOLD hasta fuente original verificable.
- **LIVEPASS:** el estado `HOLD_TIME_CONFLICT` sigue intacto y no modifica canónicos.

## Operación y seguridad

Se invocó una **FULL comparativa** [GitHub #40707082808](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40707082808) el 28/10 a partir del código probado previo al añadido de EDITA. Al documentar, seguía **EN EJECUCIÓN**, con **64 fuentes seleccionadas**; no declararla completada ni usar métricas de mitad de corrida como resultado final. `run_id=definitivo-20261028T143331Z-acfc00`.

Continúa la tarea ChatGPT a 05:00 FULL, 13:00 y 21:00 incrementales. El cron-probe GitHub no tiene todavía `schedule` comprobado. No reintroducir otro scheduler ni publicar desde este ejecutor.

**Siguiente gate:** finalizar esta FULL y hacer readback en Neon; luego un incremental puntual de EDITA para comprobar el parser, y por último revisar dry-run del Motor y el listado de los 28 pendientes por dominio. Aprobación/publicación sigue separada y bajo reglas existentes.
