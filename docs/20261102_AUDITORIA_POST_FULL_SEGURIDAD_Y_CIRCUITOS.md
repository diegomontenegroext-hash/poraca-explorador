# Por Acá — auditoría posterior a FULL: privilegios, circuitos y pendientes E2E
**Corte:** 02/11/2026 ~10:00 ART. **Método:** consultas `SELECT` exclusivamente, conector autenticado Neon y Vercel; cotejo contra los backlogs #16, #28 y #30. **No es certificado final ni autorización de DML.**

## Contexto obligatorio para no medir la base equivocada
Neon proyecto `frosty-union-52906378`, base `neondb`. La rama de **Por Acá operativa** es `br-mute-recipe-b4odj2bl` (`poraca-production`). La rama predeterminada `br-green-glade-b4lq7fz7` (`production`) **no es el corte operativo de Por Acá**. Toda prueba de esta acta usó `branch_id` explícito. Una vista antigua en la rama por defecto puede devolver cero corridas hoy; no convertir ese dato en una alarma falsa sobre Radar.

## Estado corroborado en la rama correcta
- Última FULL: `definitivo-20261102T085408Z-cc1833`, `full / complete`, inició 05:54:08 y cerró 05:59:31 ART.
- `source_checks`: **62 fuentes fetch**: 30 `ok`, 32 `index_only`, **0 errores de extracción/acceso**; adicionalmente 1 semilla `discover_only` `ok`. No contar semilla como fuente productiva de agenda.
- `listing_occurrences`: **516** registros, **282** con fecha desde 02/11; catálogo canónico **144** y entidades **135**. El acta de ejecución registra 38 nuevos y 186 reobservados; no equivalen a 38 eventos publicados.
- **Malena Muyala:** 5 registros staging para 21/11 y **0 canónicos**; falta recibo de decisión editorial independiente + admisión autorizada + lectura API/web. No autopublicar.
- **Feria Catar V Edición:** fuente original https://www.passline.com/eventos/feria-catar-v-edicion acredita 27/11/2026, 19:00–23:00, Paseo Mitre (Gorina); **0 staging / 0 canónicos** en fecha exacta. Es un testigo ideal de cobertura faltante y de canal organizador alternativo ACSBA; no aprobar en la base por investigación manual.
- El último despliegue Vercel `dpl_2wtP6ZnAeupsdswDmHc56N2NuA3q`, SHA `2531e17128b5fddb791c43d91bd006df5b69877d` figura **READY/production**, SSO habilitado. Eso no reemplaza navegación Chromium real con sesión SSO.

## Auditoría read-only de permisos legados
`poraca_definitivo_ingest` y `poraca_explorador_writer`: `LOGIN=TRUE`, membresía `neon_superuser=TRUE`, capacidad `CREATEDB/CREATEROLE=TRUE`. Para ambos, en el corte: **0 sesiones visibles**, **0 relaciones, 0 funciones, 0 esquemas y 0 ACL por defecto de su propiedad**. Estos ceros **no demuestran que ningún proceso use sus credenciales**. El rol operativo `poraca_radar_limited_prod` no es `neon_superuser`, no tiene `CREATEDB` ni `CREATEROLE`, y ya registró escritura real de staging.

El conector Vercel permitió inventariar **27 variables por nombre/tipo/entorno sin desencriptar valores**. No se comprobó con ese metadato qué cuenta PostgreSQL reside detrás de cada URL. Antes de desactivar cualquier login antiguo: verificar referencias efectivas en secretos GitHub Actions, Vercel y otras integraciones; confrontar `application_name` y actividad en ventanas de uso ordinario; conservar mecanismo de reversión; retirar **una cuenta por vez** y repetir pruebas de lectura web/ingesta normal sin introducir una FULL extra. **Ninguna revocación ejecutada.**

### SQL de reproducción: rama operativa explícita, solo SELECT
```sql
SELECT r.rolname, r.rolcanlogin, r.rolcreatedb, r.rolcreaterole,
       pg_has_role(r.rolname,'neon_superuser','member') AS elevated,
       (SELECT count(*) FROM pg_class c WHERE c.relowner=r.oid) AS owned_relations,
       (SELECT count(*) FROM pg_proc p WHERE p.proowner=r.oid) AS owned_functions,
       (SELECT count(*) FROM pg_namespace n WHERE n.nspowner=r.oid) AS owned_schemas,
       (SELECT count(*) FROM pg_default_acl a WHERE a.defaclrole=r.oid) AS default_acl_entries,
       (SELECT count(*) FROM pg_stat_activity a WHERE a.usename=r.rolname) AS visible_sessions
FROM pg_roles r
WHERE r.rolname IN ('poraca_definitivo_ingest','poraca_explorador_writer','poraca_radar_limited_prod')
ORDER BY r.rolname;
```

## Orden de cierre mínimo y verificable (sin inventar semáforos verdes)
1. **Cobertura real:** medir la siguiente FULL ordinaria posterior al clasificador de propósito y recuperación de Dionisio. Debe distinguir fuente identitaria/archivo de fuente que realmente entrega funciones. Para vinos exigir al menos un anuncio futuro extraído por el canal vigente, con prueba original; para plena resiliencia, dos canales independientes con rendimientos medidos. No considerar `HTTP 200` extracción exitosa.
2. **Admisión editorial fresca:** un expediente como Malena, decisión independiente registrada y único canon autorizado; verificar luego Neon→API→web manteniendo negativos/duplicados. Para Feria Catar, primero descubrimiento nativo en staging.
3. **Seguridad:** inventario de referencias de credenciales **real**, prueba de sustitución, deshabilitación controlada de dos logins legados, readback de ingesta y rollback. No confundir `0` sesiones instantáneas con ausencia de dependencia.
4. **Navegador SSO:** QA Chromium sobre **producción autenticada**, cuatro perfiles y 360/390/768/1440, sin desactivar Deployment Protection ni sustituir con QA local.
5. **Estabilidad:** health-v2 en FULLs ordinarias consecutivas, 3/7 días; primeros hitos posibles 05/11 y 09/11 si no hay brechas y todas resultan saludables. La primera FULL health-v2 fue el 02/11: ningún veredicto de 3d/7d puede emitirse hoy.

**Decisión:** servicio desplegado y la ingesta limitada demostrada, integridad canónica previamente certificada; **certificado global E2E retenido** hasta los cinco criterios anteriores. Mantener #16 como backlog único y #28/#30 como frentes especializados. No crear otro motor, tarea, cron ni branch.  
