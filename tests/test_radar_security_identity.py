"""Safe SQL-created limited login is recognized only after privilege proof."""
import pathlib
import sys
import unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from radar_security_identity import (
    LEGACY_LOGIN, LIMITED_LOGIN, approved_operational_login,
    approved_operational_identity,
)

class FakeCursor:
    def __init__(self, result):
        self.result = result
        self.query = None
        self.params = None
    def execute(self, sql, params=()):
        self.query = sql
        self.params = params
    def fetchone(self):
        return self.result

OK = ("neondb","frosty-union-52906378","br-mute-recipe-b4odj2bl",
      True,False,False,False,False,True,False,False)

class IdentityTests(unittest.TestCase):
    def test_legacy_compatible_without_db_query(self):
        cur=FakeCursor(None)
        self.assertTrue(approved_operational_login(cur,LEGACY_LOGIN))
        self.assertIsNone(cur.query)

    def test_limited_only_after_strict_catalog_proof(self):
        cur=FakeCursor(OK)
        self.assertTrue(approved_operational_login(cur,LIMITED_LOGIN))
        self.assertEqual(cur.params,(LIMITED_LOGIN,))
        self.assertIn("pg_catalog.pg_roles",cur.query)

    def test_neon_superuser_never_accepted_for_new_login(self):
        fake=list(OK);fake[7]=True
        self.assertFalse(approved_operational_login(FakeCursor(tuple(fake)),LIMITED_LOGIN))

    def test_canonical_writer_never_accepted(self):
        fake=list(OK);fake[10]=True
        self.assertFalse(approved_operational_login(FakeCursor(tuple(fake)),LIMITED_LOGIN))

    def test_missing_scope_or_createdb_rejected(self):
        fake=list(OK);fake[8]=False
        self.assertFalse(approved_operational_login(FakeCursor(tuple(fake)),LIMITED_LOGIN))
        fake=list(OK);fake[8]=True;fake[5]=True
        self.assertFalse(approved_operational_login(FakeCursor(tuple(fake)),LIMITED_LOGIN))

    def test_unexpected_database_branch_or_role_rejected(self):
        fake=list(OK);fake[2]="wrong-branch"
        self.assertFalse(approved_operational_login(FakeCursor(tuple(fake)),LIMITED_LOGIN))
        self.assertFalse(approved_operational_login(FakeCursor(OK),"any-third-login"))
        expect=("neondb",LEGACY_LOGIN,"poraca_definitivo_scope","frosty-union-52906378","br-mute-recipe-b4odj2bl",True,False)
        row=list(expect);row[1]=LIMITED_LOGIN
        self.assertTrue(approved_operational_identity(FakeCursor(OK),tuple(row),expect))
        row[4]="wrong"
        self.assertFalse(approved_operational_identity(FakeCursor(OK),tuple(row),expect))

if __name__=="__main__":
    unittest.main()
