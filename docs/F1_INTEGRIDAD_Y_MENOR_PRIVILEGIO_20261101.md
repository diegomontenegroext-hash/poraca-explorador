# Por Acá · F1 Seguridad e integridad — ejecución 01/11/2026

<!-- PORACA_MINPRIV_QA_SQL_VERIFIED_20261101 -->
## Actualización: mecanismo limitado demostrado en QA (01/11/2026)

**La vía correcta está identificada y probada, sin modificar producción.** La [documentación oficial de Neon](https://neon.com/docs/manage/roles) aclara que los roles creados por consola, API o CLI heredan `neon_superuser`, mientras que los creados con SQL no. El error anterior fue intentar degradar roles creados con la API.

**Prueba reversible en Neon QA `br-icy-night-b4larkc3`:**
1. En una transacción con `SAVEPOINT`, `CREATE ROLE <probe> NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT`.
2. `GRANT poraca_definitivo_scope TO <probe>`, sin tocar permisos de tablas ni autorizar DDL.
3. Readback: `neon_superuser=false`; `CREATEROLE=false`; `CREATEDB=false`; `INSERT` en `radar_definitivo.runs/source_checks/listing_occurrences=true`; `UPDATE radar_definitivo.sources=true`; `INSERT/DELETE public.radar_agenda_events=false`; `CREATE DATABASE=false`.
4. `ROLLBACK TO SAVEPOINT`; la consulta independiente verificó **cero roles residuales**. También se comprobó ausente la vieja cuenta `poraca_ingest_limited_qa_20261101`.

**Siguiente paso requerido para terminar A17**: administrador crea mediante **SQL del editor de Neon, no API** un nuevo usuario `LOGIN` de mínimo privilegio con contraseña aleatoria gestionada en un cofre; `GRANT poraca_definitivo_scope` y preflight de roles + staging y negativa canónica con credencial real, en QA primero. Requiere **actualizar atómicamente el secreto de GitHub Actions `NEON_RADAR_OPERATIONAL_DATABASE_URL` y comprobar el siguiente run ordinario/verify_only antes de inutilizar las dos identidades anteriores**. El conector GitHub disponible aquí no ofrece operación autorizada para editar Actions Secrets; no copiar claves a chats, logs o repositorios. Sin ese cutover con rollback no declarar `LEAST_PRIVILEGE PASS`. La cuenta `poraca_explorador_writer` no se toca hasta confirmar dependencias.

**Permanece abierto en PROD:** ambos logins originales siguen `neon_superuser`, CREATEDB y CREATEROLE. Ningún secreto ni acceso productivo fue modificado en esta prueba.
<!-- /PORACA_MINPRIV_QA_SQL_VERIFIED_20261101 -->


## Resultado comprobado

- **Operación vigente**: Neon proyecto `frosty-union-52906378`, rama `br-mute-recipe-b4odj2bl`, base `neondb`. 130 filas canónicas antes y después del cambio.
- **Nueva protección aplicada**: función y trigger `poraca_canonical_event_key_immutable_v1`, BEFORE UPDATE OF `event_key`. La prueba se ejecutó primero en `br-icy-night-b4larkc3` y se leyó en producción: 1 trigger nuevo ENABLED, **3 triggers en total** (DELETE, TRUNCATE, UPDATE identidad), sin modificación de registros. Migración versionada en [poraca-lp](https://github.com/diegomontenegroext-hash/poraca-lp/blob/main/sql/20261101_canonical_event_key_immutable_v1.sql).
- **Verificador reforzado**: `radar_integrity_verify.py` lee en una transacción `READ ONLY` y rol scope: un canario El Ánimo (existente), un canario Freezer (ausente) y el trigger de inmutabilidad (existente). Su decisión sigue FAIL sobre el histórico 5 recibos/18 vínculos observados/33 relaciones. CI de tests extendida para incluir pruebas del nuevo verificador; no afirmar PASS de Actions antes de su ejecución.
- **Doble evidencia**: el acto registrado en `poraca-lp/docs/PLAN_EXCELENCIA_BACKLOG_UNICO_20261030.md` prueba que Freezer se publicó anteriormente; hoy no existe `freezer-brindis-inauguracion-ciudad-de-gatos-2026-11-05` en el canon, aunque la relación aceptada #198 y el original en staging subsisten. Es una identidad dentro del P0 de 29, no un caso extra.
- **Auditoría SQL de orfandad**: [dossier read-only](../sql/20261101_p0_orphan_identity_dossier_ADMIN_READ_ONLY.sql) — 5 IDs con recibo/venue `verified_internal`, 12 IDs con observaciones sin canon y 12 sostenidos solo por relaciones. **Prohibido maquillar el FAIL** insertando canónicos falsos o elevando sedes automáticamente.

## P0 de mínimo privilegio — bloqueo identificado

La cuenta operativa `poraca_definitivo_ingest` tiene `LOGIN, CREATEROLE, CREATEDB` y pertenece a `neon_superuser`. `poraca_explorador_writer` también. Sin embargo, el rol NOLOGIN `poraca_definitivo_scope` no es miembro del grupo privilegiado y conserva permisos correctos para lecturas y escrituras de staging; carece de DML canónico.

**Ensayo aislado en rama existente de QA**: se creó el login temporal `poraca_ingest_limited_qa_20261101`. La API de Neon le asignó por defecto privilegios elevados (CREATEROLE, CREATEDB y pertenencia a neon_superuser). Los comandos `REVOKE neon_superuser` y `ALTER ROLE ... NOLOGIN` fueron rechazados con `permission denied`; no se repitieron. **La contraseña se rotó inmediatamente y no se guardó ni se distribuyó, pero la cuenta QA todavía existe con LOGIN y permisos elevados.** Debe eliminarse mediante el panel/conector Neon por un operador autorizado; **eliminar exclusivamente `poraca_ingest_limited_qa_20261101` en `br-icy-night-b4larkc3`, NUNCA las cuentas de producción**. La eliminación requiere aprobación explícita según la política de cambios destructivos. No considerar este ensayo una migración exitosa.

### Cutover propuesto y puertas obligatorias

1. Administrador Neon autorizado: establecer un mecanismo soportado para crear **un login no privilegiado real** sin `neon_superuser`, `CREATEROLE`, `CREATEDB`, propietario/DDL ni DML de `public.radar_agenda_events`. La API conectada no permitió degradar un login. No crear más roles elevados como prueba.
2. Dar a ese login únicamente pertenencia a `poraca_definitivo_scope` (o privilegios mínimos funcionalmente equivalentes), CONNECT y los grants necesarios. Ensayar en rama QA preexistente, sin tocar el secreto operativo. Comprobar `session_user` y `current_user` **después de SET LOCAL ROLE**.
3. Adaptar las comprobaciones de identidad explícitas de `src/radar_definitivo.py`, `src/radar_category_pulse.py`, `src/radar_funnel_metrics.py`, `src/radar_direct_feed_verify.py`, `src/radar_integrity_verify.py` y `src/radar_executive_gates.py`. No relajar el chequeo de proyecto/rama/database, ni permitir que una variable arbitraria lo evite.
4. En clon, probar FULL e incremental con entradas inocuas, reportes `SELECT`, y **pruebas negativas** de INSERT/UPDATE/DELETE canónico y ALTER/DROP/disable trigger. Las pruebas negativas no deben ejecutarse contra producción.
5. Solo con QA PASS y credenciales verificadas, cambio controlado del secreto `NEON_RADAR_OPERATIONAL_DATABASE_URL` por GitHub con un rollback seguro. Verificar una corrida ordinaria y una verificación `verify_only`; observar estabilidad 3/7 días reales antes de cerrar A17. No levantar deployment protection de Vercel ni añadir cron.
6. Mantener `poraca_explorador_writer` fuera de la cadena productiva; revisar dependencias de la identidad en laboratorio antes de cualquier revocación.

## Criterio ejecutivo

Protección adicional de identidad: **PASS (3 triggers activos)**. Integridad histórica: **FAIL**. Principio de menor privilegio A17: **FAIL**. Corrección integral de los 29 casos + privilegios mínimos + pruebas HTTP/SSO + estabilidad: **PENDIENTE**.

Próximo frente editorial en paralelo: procesar solo expedientes con original individual y entidad acreditada, separar actividad de sede, sub-sala, curso regular y evento puntual; no confundir propuestas con autorizaciones.
