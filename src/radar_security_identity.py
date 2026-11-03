"""Strict Neon identity gate for operational Radar; fail closed on legacy login.

Since production's verified cutover to NEON_RADAR_LIMITED_DATABASE_URL, the
previous elevated poraca_definitivo_ingest login cannot authenticate normal
Radar, executive probes or E2E verification. No automatic credential fallback.
Never accept a name from environment variables or relax project/branch scope.
"""
from __future__ import annotations

LEGACY_LOGIN = "poraca_definitivo_ingest"
LIMITED_LOGIN = "poraca_radar_limited_prod"
EXPECTED_DATABASE = "neondb"
EXPECTED_PROJECT = "frosty-union-52906378"
EXPECTED_BRANCH = "br-mute-recipe-b4odj2bl"


def approved_operational_login(cursor, login: str) -> bool:
    """Run under current transaction; prove new login cannot mutate editorial data."""
    # The 01/11 production secret has already been cut over to the limited
    # login. If it regresses to the old overprivileged credential, fail rather
    # than silently repairing ingestion by accepting superuser-like access.
    if login != LIMITED_LOGIN:
        return False
    cursor.execute("""
        SELECT current_database(),
               current_setting('neon.project_id',true),
               current_setting('neon.branch_id',true),
               r.rolcanlogin,r.rolsuper,r.rolcreatedb,r.rolcreaterole,
               r.rolreplication,r.rolbypassrls,
               pg_has_role(r.rolname,'neon_superuser','member'),
               pg_has_role(r.rolname,'poraca_definitivo_scope','member'),
               has_database_privilege(r.rolname,current_database(),'CREATE'),
               has_table_privilege(r.rolname,'public.radar_agenda_events',
                                   'INSERT,UPDATE,DELETE,TRUNCATE')
        FROM pg_catalog.pg_roles r WHERE r.rolname=%s
    """, (login,))
    return cursor.fetchone() == (
        EXPECTED_DATABASE, EXPECTED_PROJECT, EXPECTED_BRANCH,
        True, False, False, False, False, False, False, True, False, False,
    )


def approved_operational_identity(cursor, identity, expected: tuple) -> bool:
    """Keep exact database, scoped role, Neon project, branch and privilege flags."""
    if (not isinstance(identity, (tuple, list))
            or len(identity) != len(expected)
            or identity[0] != expected[0]
            or tuple(identity[2:]) != tuple(expected[2:])):
        return False
    return approved_operational_login(cursor, identity[1])
