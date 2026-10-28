# POR ACÁ — RADAR DEFINITIVO V0.2 · TRASPASO CONTROLADO DEL 28/10/2026

## Decisión y estado real

El usuario autorizó reemplazar la tarea ChatGPT por el Radar Definitivo de GitHub Actions. Se comprobó mediante el conector de Automations que `Por Acá — Sistema cultural Chat V1` (ID `6adf39eef92481918c559fdc8838e316`) quedó `is_enabled=false`; el Semáforo financiero no se tocó. `radar-paralelo.yml` es un piloto archivado (ejecución manual solamente); **el único Radar cultural de GitHub programado es `radar-definitivo.yml`.**

**Configuración ya integrada en main:** [workflow](../.github/workflows/radar-definitivo.yml), [motor](../src/radar_definitivo.py), [tests](../tests/test_radar_definitivo.py), [QA](../.github/workflows/radar-definitivo-ci.yml).

**Advertencia indispensable:** el pipeline usa `NEON_RADAR_OPERATIONAL_DATABASE_URL` si el secreto existe en GitHub; mientras falta ese secreto usa expresamente `NEON_EXPLORADOR_DATABASE_URL` y mantiene la **ingesta en la base de laboratorio**. No anunciar que GitHub está escribiendo en `neondb` hasta tener un run con `target=operational_neondb_staging` y lectura independiente en Neon. El modo provisional evita la pérdida completa de adquisición después de la pausa de ChatGPT.

## Única acción manual pendiente para cutover a Neon operativa

Abrir la consola Neon, proyecto `bitacora`, rama **`poraca-production`**, seleccionar **Database `neondb`** y **Role `poraca_definitivo_ingest`**. Copiar **connection string** con SSL desde *Connect*. En [Actions secrets del repositorio](https://github.com/diegomontenegroext-hash/poraca-explorador/settings/secrets/actions) crear `NEON_RADAR_OPERATIONAL_DATABASE_URL` con esa cadena completa. No publicar la contraseña en chat ni GitHub. No reemplazar el secreto anterior de laboratorio.

Cada vez que se ejecute, el motor verificará `current_database()=neondb`, `session_user=poraca_definitivo_ingest`, existencia del schema y a continuación ejecutará `SET ROLE poraca_definitivo_scope`. Comprueba que el rol de ejecución final no tiene permiso de INSERT en `public.radar_agenda_events`; de lo contrario aborta. Esta medida limita **las operaciones del proceso** a su esquema; el rol Neon de login se crea con membresías administradas por el proveedor, por lo que no debe confundirse esta reducción de privilegios en tiempo de ejecución con una limitación absoluta de la credencial original. Evaluar endurecimiento del rol más adelante con soporte de Neon.

## Horarios y límites

`FULL`: **03:17 ART todos los días** (`17 6 * * *` UTC). Puede recorrer hasta 75 fuentes; el inventario actual registra 63 webs con `monitoring_mode=fetch`. Abre hasta 6 vínculos por fuente y prioriza las webs nunca visitadas o menos recientes. Si se agota el presupuesto, las fuentes restantes quedan pendientes.

`INCREMENTAL`: **11:17 y 19:17 ART** (`17 14,22 * * *` UTC). Selecciona sólo fuentes vencidas por `next_due_at`, hasta 45 fuentes y 4 vínculos por fuente, con backoff por fallo y reintento temprano de índices vacíos.

**Límites por corrida:** 360 solicitudes HTTP, hasta 26 por host, hasta 24 URLs exactas de Instagram, **mínimo 4 segundos entre accesos a Instagram** y 200 ms mínimos entre solicitudes en general; presupuesto interno 24 minutos y timeout GitHub 38 minutos. Cada HTTP usa timeout de 10 s. Ante 429, se bloquea el host por el resto del run. La próxima visita no salta artificialmente su cola.

Los horarios son una solicitud al scheduler de GitHub, que puede retrasar u omitir ejecuciones; no prometer puntualidad antes de observar `event=schedule`.

## Fuentes y alcance real

Importado desde las tablas históricas de Radar sin alterar los originales:
- **225 URLs/fuentes catalogadas**, de ellas **63 webs activas**, 39 URLs históricas retenidas en revisión y 123 perfiles de Instagram para descubrimiento indirecto.
- Perfiles (`discover_only`) **no** implican lectura de feed: se intentan únicamente URLs públicas de publicaciones `/p/` y reels `/reel/` descubiertas en agendas/medios.
- El inventario incluye Luti, La Selva Yoga, Dionisio, 0221, El Día, Genda, Teatro Metro/Ópera, Alternativa Teatral, etc. Sin atribuirles cobertura observada si no se abrió cada una.
- El motor conserva URLs completas con parámetros de fecha pertinentes y vínculos de Instagram, y registra referencias a imágenes OG sin descargar ni publicar imágenes. Algunas agendas generadas con JS pueden dar índice vacío, que se registra como `index_only`.

## Neon: dos bases, destino operativo preparado

**Laboratorio:** DB `poraca_explorador`, schema `radar_definitivo`. Primera corrida histórica de GitHub `#40630215172` en modo full finalizó `success` en GitHub y `partial` en adquisición: 36 fuentes intentadas, 33 accesibles, 66 candidatos, 11 URLs IG. Esos datos son sólo candidatos.

**Operativa:** DB `neondb`, schema `radar_definitivo` ya creado sin tocar los datos públicos existentes. Se migraron como *baseline candidato*, no como eventos confirmados, **225 fuentes, 129 entidades candidatas y 66 candidatos con sus 71 atribuciones**. Tablas separadas:
- `sources`: papeles, cadencia, prioridad, cursor y errores.
- `runs` y `source_checks`: inicio/fin, runId, cobertura realmente realizada, errores/timed out y estadísticas propias.
- `candidates` y `candidate_sources`: deduplicación por URL, registro de apariciones y evidencia original.
- `link_edges` y `media_references`: referencias de enlaces y fotos, sin descarga.
- `event_occurrences`: ocurrencias de evento estructuradas desde JSON-LD y fechas válidas, **siempre** `observed_unverified`.
- `entities`: lugares/organizaciones descubiertos y perfil de origen, **siempre** propuestas.
- Vistas `run_live_progress` y `operational_health` para monitoreo.
- `motor_observations_preview` prepara una sola observación por ocurrencia compatible con `radar_v3_source_observations`, sin escribir ni aceptar eventos en esa tabla todavía.
- `possible_duplicate_events` ofrece detección conservadora de posibles duplicados entre URLs distintas por título normalizado, fecha y sede: sólo diagnóstico, no fusión automática.

**No se modificaron** `public.radar_agenda_events`, `public.radar_v3_source_observations`, `public.radar_v3_source_sweep_checks`, las reglas del Motor/Puente ni el backend privado. La API actual sigue leyendo sus contratos previos. El nuevo Radar no debe declararse sustituto **funcional completo de la cadena Motor → Puente → Web** hasta integración y QA separados.

## Calidad, deduplicación y QA

- Una URL reencontrada actualiza `seen_count` y `last_seen_at`, y suma su fuente; no genera un candidato nuevo.
- Una ocurrencia de fecha sólo se estructura si hay página realmente abierta, JSON-LD `Event`, fecha válida cercana (14 días pasados a 365 futuros) y título concreto. **No equivale a evento confirmado**.
- La categoría inferida es un borrador: `cine, teatro, musica, danza, arte, formacion, comunidad`.
- Duplicados *semánticos* con distintas URLs, conflictos de horarios/salas y acreditación de primera fuente aún requieren Motor.
- Las fuentes de Instagram pueden ser 429; la ausencia de acceso se registra, no se reporta como éxito o novedad.
- QA sintáctico y unitario corre en GitHub antes de que el workflow de producción haga solicitudes.
- El esquema operativo no es un destino de publicación directa: requiere posterior habilitación del contrato Motor 5.2 con reconciliación estricta.

## Lecturas independientes (Neon → neondb → poraca-production)

```sql
SELECT * FROM radar_definitivo.operational_health;
SELECT * FROM radar_definitivo.run_live_progress ORDER BY started_at DESC LIMIT 10;
SELECT kind,review_state,count(*) FROM radar_definitivo.candidates GROUP BY 1,2;
SELECT event_date,event_time,venue,proof_url,review_state
FROM radar_definitivo.event_occurrences ORDER BY first_seen_at DESC LIMIT 30;
SELECT * FROM radar_definitivo.motor_observations_preview LIMIT 30;
SELECT * FROM radar_definitivo.possible_duplicate_events LIMIT 30;
```

## Próximas mejoras reales

1. Validar primer run **operativo** después de instalar `NEON_RADAR_OPERATIONAL_DATABASE_URL`; contrastar los contadores de `neondb` con el Summary GitHub.
2. Implementar adaptadores por fuente (RSS, eventos institucionales, selectores de calendario, ticketera, agenda por día); no declarar que el extractor genérico resuelve automáticamente JS.
3. Reconciliación por título normalizado + fecha + hora + sede entre URLs diferentes, y pruebas de cambios/cancelaciones.
4. Ampliar descubrimiento indirecto desde redes sin eludir 429, y determinar recencia real de cada fuente.
5. Cuando exista evidencia y QA, habilitar una promoción controlada **sólo de observaciones no confirmadas** hacia Motor, sin aceptar eventos automáticamente ni alterar fichas por defecto.
6. Tras varios días estables, decidir si conviene dar de baja definitivamente el piloto manual.
