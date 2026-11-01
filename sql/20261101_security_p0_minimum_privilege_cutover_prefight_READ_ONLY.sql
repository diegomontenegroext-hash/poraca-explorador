-- POR ACA / SECURITY P0 | ROLE CUTOVER PREFLIGHT | SELECT ONLY
-- Evidence for a human-authorized migration; does NOT create roles, grant,
-- revoke, change secrets, or touch production tables.
WITH roles AS (
 SELECT r.rolname,r.rolcanlogin,r.rolcreaterole,r.rolcreatedb,
  pg_has_role(r.rolname,'neon_superuser','member') AS privileged,
  pg_has_role(r.rolname,'poraca_definitivo_scope','member') AS scoped,
  has_table_privilege(r.rolname,'public.radar_agenda_events','INSERT') AS canon_insert,
  has_table_privilege(r.rolname,'public.radar_agenda_events','UPDATE') AS canon_update,
  has_table_privilege(r.rolname,'public.radar_agenda_events','DELETE') AS canon_delete,
  has_table_privilege(r.rolname,'radar_definitivo.runs','INSERT') AS runs_insert,
  has_table_privilege(r.rolname,'radar_definitivo.source_checks','INSERT') AS checks_insert,
  has_table_privilege(r.rolname,'radar_definitivo.listing_occurrences','INSERT') AS listings_insert,
  has_table_privilege(r.rolname,'radar_definitivo.sources','UPDATE') AS sources_update
 FROM pg_roles r
 WHERE r.rolname IN ('poraca_definitivo_ingest','poraca_explorador_writer',
                     'poraca_definitivo_scope','poraca_motor_qa')
)
SELECT *,CASE
 WHEN rolname='poraca_definitivo_scope'
   AND NOT rolcanlogin AND NOT privileged AND NOT rolcreaterole AND NOT rolcreatedb
   AND NOT canon_insert AND NOT canon_update AND NOT canon_delete
   AND runs_insert AND checks_insert AND listings_insert AND sources_update
   THEN 'SCOPE_READY_FOR_LIMITED_LOGIN_CUTOVER_TESTS'
 WHEN rolname='poraca_motor_qa' AND NOT privileged
   AND NOT canon_insert AND NOT runs_insert AND NOT listings_insert
   THEN 'WEB_READER_SCOPE_SAFETY_PASS'
 WHEN rolcanlogin AND (privileged OR rolcreaterole OR rolcreatedb OR
     canon_insert OR canon_update OR canon_delete)
   THEN 'P0_OVERPRIVILEGED_DO_NOT_ROTATE_BLINDLY'
 ELSE 'MANUAL_INSPECTION_REQUIRED' END AS verdict,
 false AS writes_performed,
 false AS production_credentials_changed
FROM roles ORDER BY rolname;