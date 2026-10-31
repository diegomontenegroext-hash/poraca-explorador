# POR ACÁ — inventario de Neon y ensayo adaptativo (31/10/2026)

**Estado: auditoría + simulación reproducible; no limpieza física, sin nuevos Radar FULL, sin alterar producción.**
Branch operativa comprobada `poraca-production` (`br-mute-recipe-b4odj2bl`), DB `neondb`. El proyecto Neon cuenta con 2 ramas de 10 posibles y tope lógico de **1 GiB por rama**; la rama operativa tiene **88.645.632 bytes (~84,5 MiB)**. No hay urgencia de espacio. **No confundir la rama `production` con la rama operativa `poraca-production`.**

## 1. Inventario real, por dominio

- **Capa editorial que nunca se vacía por un test:** 161 `public.radar_agenda_events`, 63 publicados, 40 futuros; entidades, conocimiento, validaciones y relaciones del Motor y web. Permanecen sus IDs y vínculos.
- **Capa de aprendizaje Radar que debe permanecer:** 228 fuentes, 677 funciones de staging (403 actuales/futuras, 274 pasadas), 264 candidatos, 40 corridas de Radar, 952 chequeos. Contiene memoria de aparición y repetición, paridad con originales y señales de cambio. NO limpiar para fabricar una métrica de «nuevo» desde cero.
- **Capa editorial provisional que amerita política de retención/archivo, no borrado automático:** `public.editorial_motor_assessments_v3`: **16.547 evaluaciones en 28 ejecuciones**, tabla ~32 MB; últimas 3 ejecuciones 2.185 filas, anteriores **14.362 filas**. Son evaluaciones con diferentes decisiones y estados, no basura demostrada. Comprobar consumidores, referencias, auditoría, exportación íntegra y restauración antes de archivar o eliminar.
- **Snapshots/controles menores:** `radar_lab_snapshots`, `radar_v3_checkpoints`, `radar_definitivo.canonical_baseline_snapshots`, `public.radar_v3_source_observations`; no confundir copias de corte con contenido editorial. Evaluar su obsolescencia uno a uno tras identificar lectores y dueños.

## 2. Ensayo ejecutado de los 228 registros de fuente (solo lectura)

Código reproducible:
- `src/radar_adaptive_shadow.py`: políticas puras por señales, sin fetch ni escritura.
- `sql/20261031_radar_adaptive_shadow_readonly_v1.sql`: 7 días de histórico de `source_checks` + observaciones + evidencia primaria, sin cambiar `priority`, `cadence_hours`, ni `monitoring_mode`.
- `tests/test_radar_adaptive_shadow.py`: casos para original, secundaria, institucional sin fecha, inactiva, nueva, perfil indirecto, modo review y prohibición de admisión.
- Único workflow QA existente. Este ensayo **no ejecuta el nuevo Radar ni prueba cambios de formato reales**.

Resultados observados, **hipótesis no decisiones**:

| Modo de seguimiento hipotético | Fuentes |
|---|---:|
| priorizar_original | 10 |
| reconciliar_agenda_secundaria | 5 |
| exploracion_controlada | 3 |
| verificar_utilidad_antes_de_reducir | 24 |
| diagnosticar_canal_o_valor_institucional | 20 |
| explorar_si_hay_evidencia (review) | 43 |
| exploracion_indirecta_no_feed | 123 |

El resultado observa 228 fuentes, con **62 fetch**. Más volumen de agenda secundaria no significa eventos aprobados; una fuente institucional sin funciones puede ser importante para enriquecer un lugar.

## 3. Cómo hacer un «reinicio limpio» sin destruir evidencia

**Paso 1 — congelar control:** capturar conteos + identidades + referencia de código + baseline de 161 canónicos, y persistir reporte en control de cambios. Anotar exactos 40 eventos futuros y 63 publicados, nunca borrarlos por limpieza de Radar.

**Paso 2 — aislar experimento:** crear una rama Neon temporal de ensayo **solamente al implementar un runner separado**. Prohibido redirigir el secreto de producción al laboratorio; el guard de identidad y permisos lo debe rechazar. En la rama de ensayo, separar la capa editorial y los datos de referencia de la salida que genera el algoritmo; usar una tabla/namespace de ensayo distinto y *no permitir* escritura en canónicos. No ejecutar en paralelo el cron productivo ni aumentar presupuesto de requests.

**Paso 3 — replay A/B verificable:** congelar conjunto de casos históricos; medir extractor actual versus biblioteca generalizada bajo **mismo input, presupuesto y reloj**. Probar al menos: Genda/Al Pedo, cartelera oficial, institución sin fecha, sitio con estructura cambiada, feed ICS, calendario JS, nueva fuente desconocida, múltiples funciones, fuente inaccesible/429 y yoga/cerámica/vinos. Si no hay evidencia histórica HTML para replay, obtenerla mediante captura legal y respetuosa en laboratorio, no inventarla.

**Paso 4 — criterio de adopción:** cero eventos fabricados y cero escrituras editoriales; paridad de recuperación de originales con el extractor actual, menos relecturas inútiles, conservación de cobertura de circuitos minoritarios, deduplicación de la misma sesión sin perder horarios distintos, y adaptación demostrada a plantillas nuevas. Aceptar por estratos con reversión; no usar la cantidad de enlaces como meta de excelencia.

**Paso 5 — eventual depuración física:** solamente después de respaldo recuperable, análisis de dependencias, evaluación de retención y autorización explícita del propietario; preferir **archivar ejecuciones antiguas del Motor** y conservar últimos resúmenes/deltas. No ejecutar `DROP`, `DELETE`, `TRUNCATE` o `VACUUM FULL` en esta intervención. El espacio recuperado no debe ser el criterio primario.

## 4. Próxima ejecución real del Radar

La versión actual **todavía no implementa** selección automática de estrategias, detección de deriva ni ajuste automático de frecuencia. NO anunciar «Radar adaptativo funcionando». La primera nueva corrida real sólo se habilita tras implementar la estrategia genérica en modo sombra y probarla en un runner que no escriba producción. Mientras tanto la agenda 05 FULL / 13 y 21 incremental sigue inalterada y ofrece un baseline vivo.

**Conclusión:** limpiar a ciegas dañaría el aprendizaje; un **replay limpio, aislado y comparativo** permite acelerar la evolución sin sacrificar cobertura ni mezclar datos productivos.
