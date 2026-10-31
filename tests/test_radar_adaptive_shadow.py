import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from radar_adaptive_shadow import assess


class RadarAdaptiveShadowTests(unittest.TestCase):
    def row(self, **overrides):
        return dict(monitoring_mode="fetch", checks_7d=5, index_only_7d=0,
                    failed_7d=0, new_7d=0, primary_new_7d=0,
                    future_sessions=0, **overrides)

    def test_primary_venue_and_different_site_name_not_required(self):
        got=assess({"monitoring_mode":"fetch","checks_7d":7,
                    "primary_new_7d":4,"new_7d":5,"future_sessions":3})
        self.assertEqual(got["mode_shadow"],"priorizar_original")
        self.assertEqual(got["score_shadow"],33)

    def test_secondary_agenda_needs_reconciliation(self):
        got=assess({"monitoring_mode":"fetch","checks_7d":5,
                    "new_7d":40,"primary_new_7d":0,"index_only_7d":2})
        self.assertEqual(got["mode_shadow"],"reconciliar_agenda_secundaria")
        self.assertEqual(got["score_shadow"],36)

    def test_institutional_index_must_not_be_dropped(self):
        got=assess({"monitoring_mode":"fetch","checks_7d":3,
                    "index_only_7d":3,"new_7d":0,
                    "source_role":"institutional_program",
                    "name":"Un nombre que no importa"})
        self.assertEqual(got["mode_shadow"],"diagnosticar_canal_o_valor_institucional")
        self.assertFalse(got["changes_to_sources"])

    def test_no_yield_with_successful_reads_is_not_immediate_deletion(self):
        got=assess({"monitoring_mode":"fetch","checks_7d":12,"new_7d":0})
        self.assertEqual(got["mode_shadow"],"verificar_utilidad_antes_de_reducir")

    def test_exploration_kept_for_new_source_without_past_visits(self):
        got=assess({"monitoring_mode":"fetch","checks_7d":0})
        self.assertEqual(got["mode_shadow"],"exploracion_controlada")
        self.assertEqual(got["confidence"],"insuficiente")

    def test_instagram_account_never_implies_feed_scan(self):
        got=assess({"monitoring_mode":"discover_only","checks_7d":0})
        self.assertEqual(got["mode_shadow"],"exploracion_indirecta_no_feed")

    def test_review_mode_does_not_promote_without_evidence(self):
        got=assess({"monitoring_mode":"review","checks_7d":0})
        self.assertEqual(got["mode_shadow"],"explorar_si_hay_evidencia")

    def test_no_mutations_or_approvals(self):
        for facts in (
          {"monitoring_mode":"fetch","checks_7d":9,"primary_new_7d":8},
          {"monitoring_mode":"fetch","checks_7d":6,"index_only_7d":6},
          {"monitoring_mode":"discover_only","new_7d":5},
        ):
            result=assess(facts)
            self.assertEqual(result["action_state"],"DRY_RUN_ONLY")
            self.assertFalse(result["changes_to_sources"])
            self.assertFalse(result["changes_to_editorial"])
            self.assertFalse(result["auto_publish"])


if __name__ == "__main__":
    unittest.main()
