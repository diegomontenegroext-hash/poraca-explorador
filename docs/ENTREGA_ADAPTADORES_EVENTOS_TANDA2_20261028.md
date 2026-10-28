# Por Acá — entrega Radar de eventos, segunda tanda · 28/10/2026

**Estado:** integrado en `main`, ensayos reales GitHub y lectura Neon operativa confirmados. Foco exclusivamente en EVENTOS. No se actualizó la API, web, canónicos ni entidades.

## 1. Problemas reproducidos y correcciones

- **Genda / Agenda La Plata:** con HTTP tradicional se abrían páginas `?fecha=` pero los eventos visibles en navegador no llegaban como funciones. Se añadió `src/radar_genda_browser.py`: Chrome/Playwright sólo en el dominio `agendalaplata.ar`, máximo cinco URLs de fecha por corrida, sin login, sin recursos de imagen/fuentes y con límites explícitos. Obtiene el **texto visible realmente renderizado** y el adaptador transforma cada tarjeta en función con **título, fecha, hora, sede y URL de agenda**. Se eliminó una doble lectura causada por mirar por delante desde títulos/categorías. Fechas: hoy/mañana siempre que estén enlazadas, más tres días de rotación entre los enlaces públicos de las siguientes semanas; no se construyen URLs inexistentes.
- **Ópera La Plata:** el parser ahora recorre títulos de cartelera oficial aunque estén separados por wrappers Elementor largos, recupera la **fecha de cada concierto** y conserva el enlace **Livepass efectivo del organizador**, sin inventar hora desde el slug ni deducir horarios de tickets ajenos.
- **Alternativa Teatral:** se conserva la rotación de URLs originales de la baseline y las funciones independientes por fecha/hora para una misma obra; nuevas páginas rotadas aportaron datos adicionales.
- **No entidades:** `RADAR_ENABLE_ENTITY_PROPOSALS` continúa desactivado por defecto. Instagram sigue con límites anteriores y fuentes de perfiles no scrapeadas.
- **Métricas por run:** nuevo resumen de `listings` (funciones leídas en la corrida, incluidas revisitas) y `new_listings` (funciones **insertadas por ese run**, calculadas por `first_run_id` en Neon) para distinguir novedades de memoria heredada. Su primer readback será en el próximo run posterior al commit; **no** atribuirlo retroactivamente a ejecuciones anteriores.

## 2. Evidencias de ejecución

### FULL con Ópera / Alternativa
[GitHub run #40691259009](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40691259009), evento `push`, conclusión GitHub `success`, Neon `status=partial` con **63/63 fuentes revisadas, 30 con adquisición útil, ocho URLs candidatas nuevas**. Se recuperaron **8 fechas del Ópera**, sin hora; la rotación de Alternativa elevó su acumulado a **22 funciones**. Esto no constituye 8 funciones ya verificadas.

### Incremental focalizada de Genda
[GitHub run #40692355731](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40692355731), `push`, `SUCCESS`, Neon `run_id=definitivo-20261028T125914Z-5f475c`, `mode=incremental`, `status=complete`, `sources_selected=1`, `sources_checked=1`, `sources_success=1`, `candidates_new=2`.

**Resultado verificable: 32 funciones Genda guardadas**, método `genda_dated_listing`, todas `review_state=observed_unverified`. Ejemplos efectivamente recuperados: Select/EcoSelect del 28–29/10, Play (Teatro Argentino, 29/10 19:30), teatro, actividades, recitales y programación del 28–29/11. Cada fila conserva fecha, hora, lugar y URL de página fechada; **fuente secundaria, no aceptación automática**. Las 32 funciones NO son 32 eventos necesariamente nuevos para Por Acá.

### Corpus al cierre del ensayo
`radar_definitivo.listing_occurrences` contiene:
- **32** Genda (fecha, hora, sede, fuente secundaria);
- **22** Alternativa (funciones por obra);
- **9** Casa Metro;
- **8** fechas oficiales del Ópera (horarios todavía ausentes).
**Total 71 registros de funciones en staging**, no 71 eventos públicos nuevos.

Paridad con fotografía fija de **51 eventos** en `baseline_event_parity_v2`: **12** `original_date_time_match`, **2** `time_or_identity_conflict_review`, **37** `not_recovered` bajo el criterio actual. Las coincidencias Genda secundarias que no enlazan original pueden ser útiles pero requieren corroboración y resolución de identidad; no declararlas equivalencia fuerte.

Control de calidad de observaciones (SELECT-only `observation_mapping_preview_v1`): **34 HOLD_SECONDARY_SOURCE**, **24 ALREADY_IN_PUBLIC_OBSERVATIONS**, **16 HOLD_SOURCE_NOT_AUTHORIZED**, **9 READY_FOR_MANUAL_ORIGINAL_REVIEW**, **8 HOLD_MISSING_VENUE**, **6 HOLD_MISSING_TIME**, **4 HOLD_TIME_CONFLICT**. Son filas/múltiples representaciones, no cantidad de eventos canónicos ni trabajo automáticamente admitido.

## 3. QA y operación

- QA GitHub final [#40692733353](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40692733353) `SUCCESS`, incluyendo fixture de múltiples funciones, Genda en texto visible, tarjetas divididas entre líneas, URL segura, rotación de fechas y grilla larga de Ópera. Dos corridas de QA intermedias fallaron por detección duplicada en el parser y fueron corregidas antes del ensayo final; no ocultar estos fallos históricos.
- **No hubo ninguna ejecución `event=schedule` de GitHub** en el historial observado hasta este corte. Piloto `radar-cron-probe.yml` registró por ahora sólo control positivo `push`, sin `schedule`. Continúa aislado.
- Se mantiene **UNA tarea GPT** que dispara GitHub **05:00 FULL / 13:00 y 21:00 incrementales ART**, además de ensayos controlados etiquetados `bootstrap`. La tarea recolectora ChatGPT antigua permanece pausada.
- No se borró ningún dato, no se insertó en `public.radar_v3_source_observations` ni `public.radar_agenda_events`, no se publicó a Vercel ni se reabrió el Puente.

## 4. Próximos gates

1. **Paridad P0:** abordar **37/51** sin coincidencia en el cotejo estricto. Priorización por fuente: Teatro Metro, Teatro Argentino, Lumen Artis, Livepass y Select/EcoSelect, además de los casos de redes sin post original accessible. Resolver los dos horarios en HOLD (Carmen Sánchez Viamonte y Benjamín Amadeo).
2. **Genda como descubridor secundario:** ampliar corroboración contra páginas originales de cada sala/ticketera; las 32 filas secundarias no se convierten automáticamente en agenda pública. Conservar enlaces completos y múltiples sesiones cinematográficas.
3. **Cadena posterior:** mantener `observation_mapping_preview_v1` sólo lectura, preparar adaptación y lote de prueba que respete fuentes autorizadas. **Primera escritura en observaciones públicas permanece pendiente de revisión y autorización**, sin permiso de aceptar automáticamente.
4. **Operación:** verificar por cada slot GPT → push GitHub → Neon y la métrica `new_listings`. No reactivar cron del Radar principal mientras el piloto aislado no demuestre `schedule`.

**Backlog:** `poraca-lp#16` maestro; `#28` captación; `#10` reglas; `#7` QA y continuidad. No sumar ejecutores ni procesos paralelos.
