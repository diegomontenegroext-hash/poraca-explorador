"""Strict and transitional Neon identity gate for Radar operational cutover.

The legacy elevated login remains accepted temporarily for continuity.
Only the named SQL-created limited login can be added. Never accept a
name from environment variables or relax project/branch scoping.
"""
from __future__ import annotations

LEGACY_LOGIN = "poraca_definitivo_ingest"
LIMITED_LOGIN = "poraca_radar_limited_prod"
EXPECTED_DATABASE = "neondb"
EXPECTED_PROJECT = "frosty-union-52906378"
EXPECTED_BRANCH = "br-mute-recipe-b4odj2bl"


def approved_operational_login(cursor, login: str) -> bool:
    """Run under current transaction; prove new login cannot mutate editorial data."""
    if login == LEGACY_LOGIN:
        # Compatible only until a successful, authorized credential cutover.
        return True
    if login != LIMITED_LOGIN:
        return False
    cursor.execute("""
        SELECT current_database(),
               current_setting('neon.project_id',true),
               current_setting('neon.branch_id',true),
               r.rolcanlogin,r.rolsuper,r.rolcreatedb,r.rolcreaterole,
               pg_has_role(r.rolname,'neon_superuser','member'),
               pg_has_role(r.rolname,'poraca_definitivo_scope','member'),
               has_database_privilege(r.rolname,current_database(),'CREATE'),
               has_table_privilege(r.rolname,'public.radar_agenda_events',
                                   'INSERT,UPDATE,DELETE,TRUNCATE')
        FROM pg_catalog.pg_roles r WHERE r.rolname=%s
    """, (login,))
    return cursor.fetchone() == (
        EXPECTED_DATABASE, EXPECTED_PROJECT, EXPECTED_BRANCH,
        True, False, False, False, False, True, False, False,
    )


def approved_operational_identity(cursor, identity, expected: tuple) -> bool:
    """Keep exact database, scoped role, Neon project, branch and privilege flags."""
    if (not isinstance(identity, (tuple, list))
            or len(identity) != len(expected)
            or identity[0] != expected[0]
            or tuple(identity[2:]) != tuple(expected[2:])):
        return False
    return approved_operational_login(cursor, identity[1])
