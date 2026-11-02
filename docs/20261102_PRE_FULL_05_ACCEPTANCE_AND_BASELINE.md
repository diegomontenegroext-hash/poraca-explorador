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

**API web protegida:** en el preflight la home, `/api/agenda` y `/api/approved-directory` respondieron HTTP 200 por conector Vercel autenticado. `/api/agenda` expuso 139 canónicos (incluye histórico), 48 candidatos en primera página, continuidad `discoveryCursor`; minidirectorio 51 entidades aprobadas con prueba de identidad. SSO sigue activo y noindex; no hay despliegue adicional. La diferencia entre 139 y 144 corresponde a filtros/historial/alias y NO debe tratarse como cinco pérdidas sin auditar IDs.

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
