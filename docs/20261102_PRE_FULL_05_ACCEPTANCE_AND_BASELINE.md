# Preparación y aceptación — FULL 05:00 ART del 02/11/2026

**Única programación:** automatización ChatGPT «Por Acá — Radar GitHub 3 veces al día» (05 FULL; 13 y 21 incrementales condicionales). Workflow GitHub `radar-definitivo.yml` disparado por cambio de `ops/radar-fallback-trigger.txt`. **No lanzar otra FULL para medir la primera**.

## Línea base observada, alrededor de 00:08 ART (02/11)

**Neon operacional:** proyecto `frosty-union-52906378`, rama `br-mute-recipe-b4odj2bl`, base `neondb`.

| Indicador | Corte anterior |
|---|---:|
| Fuentes fetch activas / sin circuito | 62 / 0 |
| Última FULL (01/11 18:25 ART), estado | `partial` |
| Fuente HTTP ok / index_only / otros | 30 / 32 / 0 |
| Registros detectados por corrida | 259 |
| Nuevos / reobservados | 40 / 219 |
| Evidencias primarias completas | 58 |
| Posibles duplicados, no necesariamente reales | 31 |
| Eventos admitidos por esa corrida | 0 (no es publicador) |
| Staging total / futuros | 478 / 244 |
| Canónicos totales / aún vigentes | 144 / 12 |
| Canónicos vigentes confirmados | consultar localmente, sin arrastrar cifras de día anterior |
| Entidades / relaciones culturales | 135 / 170 |
| Retenciones futuras en control editorial | 2 |
| Evidencias primarias correlacionadas en vista | 112/144 |
| Rol operativo nuevo | `poraca_radar_limited_prod`, escritura staging SÍ, canon NO |
| Primera FULL operativa bajo el rol limitado | **pendiente** |

La última FULL usó el contrato `poraca-health-v1`, donde 32 `index_only` rebajaban adquisición a parcial aunque no fueran errores HTTP. El próximo Radar construye `poraca-health-v2`: distinguir **acceso OK**, **extracción sin sesiones (index_only)**, **fallo real de conexión/parsing**, y **aceptación editorial separada**. Salud de adquisición verde NO significa que 62/62 fuentes produjeron actividades.

**API web protegida:** preflight real por conector Vercel autenticado **HTTP 200** en home, `/api/agenda` y `/api/approved-directory`; `/api/agenda` reporta **139 eventos canónicos** (incluido histórico) y sus **139 descubrimientos independientes** repartidos en **3 páginas de 48 + 47 + 44**, `discoveryCursor` hasta `hasMore=false`, **0 IDs duplicados**, **0 candidatos con `publicationApproved=true`**, **0 candidatos sin URL HTTPS**, **53 `RADAR_DIRECT` + 86 `EDITORIAL_LEGACY`**; minidirectorio 51 entidades con identidad aprobada. Son dos colecciones distintas: **139 eventos ≠ 139 descubrimientos** aunque coincida el número. La ventana temporal móvil de la API cambió el total de descubrimientos respecto del corte 1/11 (159): no inferir pérdidas sin igualar fechas. SSO sigue activo y noindex; no hay despliegue adicional. La diferencia entre 139 y 144 corresponde a filtros/historial/alias y NO debe tratarse como cinco pérdidas sin auditar IDs.

## Certificación posterior a las 05:00 (READ-ONLY)

Ejecutar `sql/20261102_05_FULL_POSTRUN_ACCEPTANCE_READ_ONLY.sql`. Registrar URL del **único** workflow correspondiente a slot `2026-11-02 / 05`, y su conclusión GitHub, RUN_ID Neon, estado, timestamps, `health.schema`, controles, fuentes y embudo. La primera corrida real **debe escribir staging** con la cuenta limitada. Buscar errores `permission denied`, errores HTTP de fuente, ejecución sin cierre y guardas.

Puertas separadas:

1. **Orquestación / escritura:** automation activó slot 05 solo una vez; workflow concluyó; nuevo `run_id` `full`; fuentes revisadas; `health-v2` emitido; role autorizado sin `neon_superuser`. Si aún corre, `PENDING`, no FAIL.
2. **Calidad del rendimiento:** comparar con línea base 30 OK / 32 index_only y 40 nuevos / 219 reobservados / 58 evidencias primarias. Una fuente `index_only:200` puede no tener anuncios o no entregar HTML útil, no equipararla a éxito pleno. Analizar prioridad El Día, Centro de Arte, Dionisio y rubros yoga/vino/under/talleres/deporte por cobertura. Cero eventos nuevos **no** implica cero fuentes revisadas.
3. **No duplicación / histórico:** `new`, `seenAgain`, `possibleDuplicates` tienen semántica independiente. Cero pares canónicos exactos pendientes, no depurar registros de staging automáticamente. No borrar 126 históricos por calendario ni inferir que ocurrieron.
4. **Editorial:** conteo `pendingEditorial` y `matchedPublished` **sin autopromoción**; 2 próximos `to_verify` mantienen cuarentena. La continuidad staging→revisión→eventos publicados se mide aparte del canal candidatos→API. La FULL no debe crear canónicos ni identidades nuevas aprobadas.
5. **API real / web:** GETs con SSO por conector Vercel y paginado `discoveryCursor` a final. Comparar al menos IDs y cantidad de descubrimientos; comprobar que un candidato nuevo pueda verse en bandeja `RADAR_UNVERIFIED`, sin aparecer duplicado como `confirmed`. El minidirectorio sigue siendo de identidad, no prueba de agenda del espacio.
6. **Estabilidad:** solo el próximo run `health-v2` inicia evidencia real de 3/7 días. No se da PASS por una FULL. Esperar resultados naturales sin nuevos crons ni builds.

**Semáforo global honesto:** `FULL_STAGING_OPERABLE` no significa `PUNTA_A_PUNTA_CERTIFICADO`; separar ejecución, extracción, tratamiento editorial, transporte API, UX y estabilidad. Si la FULL falla, la credencial antigua está guardada en GitHub para reversión *explícita* por responsable autorizado, pero no hay fallback silencioso ni permiso para debilitar seguridad/SSO.

**Intervención del usuario:** ninguna en esta preparación. La única actuación humana posterior será si un gate real falla y requiere una decisión administrativa acotada.


<!-- CIERRE_VERIFICACION_20261102_0030_ART -->
## Cierre de preflight verificado por conectores — 02/11/2026, antes de FULL 05:00 ART

**No es certificación final ni resultado de la corrida futura.** Verificado en el repositorio `main`, Neon operacional y Vercel conectado; sin publicaciones, SQL destructivo ni disparos artificiales.

- **Matriz ejecutiva vigente en Neon (SELECT del SQL oficial): 7 PASS / 1 PARTIAL / 1 FAIL / 2 NOT_CHECKED.** PASS: ORCHESTRATION, RADAR_RECEIPT, SOURCE_FETCH_HEALTH, RUN_FUNNEL, EDITORIAL_ADMISSION, CANONICAL_INTEGRITY, COVERAGE_BY_CIRCUIT. PARTIAL: STABILITY (aún sin 3/7 días maduros). FAIL: LEAST_PRIVILEGE (identidades originales `poraca_definitivo_ingest` y `poraca_explorador_writer` aún elevadas). NOT_CHECKED: DIRECT_RADAR_AND_API_HTTP y WEB_SSO_UX, pues el SQL por definición no hace HTTP ni navegador.
- **Cutover de Radar ya realizado**: `.github/workflows/radar-definitivo.yml` usa `NEON_RADAR_LIMITED_DATABASE_URL` para ejecución, métricas y verificadores, preservando el secreto antiguo sin fallback automático. `verify_only` limitado [GitHub #41378231086](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41378231086) PASS; lectura independiente tras cutover [#41378405988](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/41378405988) PASS. No confundir verify_only con escritura real de FULL.
- **Neon sobre la identidad limitada**: `LOGIN=true`, `CREATEROLE=false`, `CREATEDB=false`, `neon_superuser=false`, puede INSERT sobre `radar_definitivo.runs` y staging y NO puede INSERT a `public.radar_agenda_events`. El P0 de identidades elevadas antiguas no se cierra hasta comprobar FULL ordinaria bajo rol limitado y después revisar dependencias/retirar privilegios con rollback administrativo.
- **Integridad basada en pruebas actuales**: 144 canónicos, 12 aún vigentes (10 confirmados, 2 retenidos), 478 staging (244 futuros), 135 entidades y 170 relaciones. 133/133 huellas canónicas históricas preservadas, 0 recibos aprobados faltantes, 0 enlaces de observaciones huérfanos, 0 canarios históricos faltantes. Las 17 relaciones aceptadas hacia 15 referencias no canónicas son **hechos de contexto** con evidencia, no sesiones admitidas; el diagnóstico heredado `P0_CANONICAL_HISTORY_BROKEN` de la función V1 no debe confundirse con pérdida física actual. Nunca inventar funciones para forzar un PASS.
- **Vercel**: proyecto `poraca-lp-privado`, despliegue producción `dpl_9Hanj2ksxYvzKrWASkxXFh6gin7Y` READY, SHA `13bd605867e68963980cc8e6b8c502fa8b1d5bd5`, SSO activo. Prueba HTTP protegida previa: home, agenda y minidirectorio 200, 139 eventos y paginación del feed 48+47+44 sin repetir IDs en el corte documentado de 02/11 00:08; no constituye nueva prueba HTTP en este cierre. QA visual privada [#41355039049](https://github.com/diegomontenegroext-hash/poraca-lp/actions/runs/41355039049) PASS con Chromium real, 7 perfiles y 360/390/768/1440, **solo build estático con API simulada**, no navegación autenticada por SSO. Backlog de UX: [poraca-lp #30](https://github.com/diegomontenegroext-hash/poraca-lp/issues/30).
- **FULL 05:00 todavía NO iniciada**: ejecutado el SQL `sql/20261102_05_FULL_POSTRUN_ACCEPTANCE_READ_ONLY.sql` y devuelto `05_FULL_NOT_YET_STARTED`; no se disparó anticipadamente. Única agenda habilitada: tarea existente ChatGPT 05 FULL; 13/21 incrementales condicionales. El workflow es disparado solo por `ops/radar-fallback-trigger.txt`.

**Próximas acciones condicionadas, sin duplicar infraestructura:** (1) controlar resultado GitHub y Neon de la FULL 05 con el SQL oficial, especialmente escritura real bajo rol limitado, `poraca-health-v2`, 62 source_checks y conteos del embudo; (2) ante fallo de permisos, NO reactivar automáticamente credencial elevada, escalar rollback explícito; (3) en revisión administrativa posterior a FULL exitosa, analizar dependencias y revocar privilegios de cuentas históricas antes de levantar LEAST_PRIVILEGE; (4) HTTP/SSO autenticado y navegador vivo por el entorno autorizado existente, sin desactivar protección; (5) madurar 3/7 días de historial real, sin simularlo. Mantener semáforo separado entre adquisición, editorial, API y UX.
