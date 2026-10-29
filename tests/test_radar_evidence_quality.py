import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
import radar_evidence_quality as qa

class CrossSourceEvidenceQualityTests(unittest.TestCase):
    def test_mirrored_secondary_is_not_primary_confirmation(self):
        base=("Play, de Samuel Beckett","2026-10-30","19:30",
              "Teatro Argentino - Centro Provincial de las Artes")
        url="https://agendalaplata.ar/?fecha=2026-10-30"
        mirror="https://alpedo.ar/?fecha=2026-10-30"
        rows=[
            (qa.AGENDA_G,*base,url,"secondary_agenda"),
            (qa.AGENDA_A,*base,mirror,"secondary_agenda"),
            (qa.AGENDA_A,*base,mirror,"secondary_agenda"),
            (qa.AGENDA_G,"Play, de Samuel Beckett","2026-10-30","20:30",base[3],url,"secondary_agenda"),
            (qa.AGENDA_A,"Play, de Samuel Beckett","2026-10-30","20:30",base[3],mirror,"secondary_agenda"),
        ]
        result=qa.summarize(rows)
        self.assertEqual(result["shared_genda_alpedo_functions"],2)
        self.assertEqual(result["secondary_keys_with_specific_primary_detail"],0)
        self.assertEqual(result["auto_accepted"],0)

    def test_dirty_venues_not_joined_and_primary_match_is_only_review(self):
        base=("Muestra de arte","2026-10-30","18:00",
              "Centro Cultural Estación Provincial")
        rows=[
            (qa.AGENDA_G,*base,"https://agendalaplata.ar/?fecha=2026-10-30","secondary_agenda"),
            (qa.AGENDA_A,"Muestra de arte","2026-10-30","18:00",
             'Centro Cultural Estación Provincial <div class="img',
             "https://alpedo.ar/?fecha=2026-10-30","secondary_agenda"),
            ("original-venue","Muestra de arte","2026-10-30","18:00",
             base[3],"https://example.org/original","primary_venue"),
            (qa.AGENDA_A,"Muestra de arte","2026-10-30","18:00",
             None,"https://alpedo.ar/?fecha=2026-10-30","secondary_agenda"),
        ]
        result=qa.summarize(rows)
        self.assertEqual(result["malformed_venue_rows"],1)
        self.assertEqual(result["missing_venue_rows"],1)
        self.assertEqual(result["shared_genda_alpedo_functions"],0)
        self.assertEqual(result["secondary_keys_with_specific_primary_detail"],0)
        self.assertFalse(qa.specific_original("https://example.org/original"))
        self.assertFalse(qa.specific_original("https://www.teatrometrolp.com.ar/entradas/cartelera"))
        self.assertTrue(qa.specific_original("https://www.teatrometrolp.com.ar/entrada/juli-bellese-100781"))
        self.assertFalse(qa.contaminated("Centro Cultural Estación Provincial"))
        self.assertTrue(qa.contaminated("Casa <div class"))
        self.assertTrue(qa.contaminated("document.querySelector()"))

    def test_primary_ticket_detail_but_not_index_counts_for_review(self):
        label=("Juli Bellese","2026-10-30","21:00","Teatro Metro")
        rows=[
            (qa.AGENDA_G,*label,"https://agendalaplata.ar/?fecha=2026-10-30","secondary_agenda"),
            ("metro",*label,"https://www.teatrometrolp.com.ar/entradas/cartelera/","primary_venue")
        ]
        self.assertEqual(qa.summarize(rows)["secondary_keys_with_specific_primary_detail"],0)
        rows.append(("metro",*label,
            "https://www.teatrometrolp.com.ar/entrada/juli-bellese-100781",
            "primary_venue"))
        self.assertEqual(qa.summarize(rows)["secondary_keys_with_specific_primary_detail"],1)
        rows.append(("metro-copy",*label,
            "https://www.teatrometrolp.com.ar/entrada/juli-bellese-100781",
            "primary_ticket_listing"))
        self.assertEqual(qa.summarize(rows)["secondary_keys_with_specific_primary_detail"],1)

    def test_different_date_time_or_venue_is_different_session(self):
        title="Obra viajera"
        rows=[
            (qa.AGENDA_G,title,"2026-10-30","21:00","Teatro Muñiz",
             "https://agendalaplata.ar/","secondary_agenda"),
            (qa.AGENDA_A,title,"2026-11-01","19:00","Sala 420",
             "https://alpedo.ar/","secondary_agenda"),
        ]
        self.assertEqual(qa.summarize(rows)["shared_genda_alpedo_functions"],0)
        self.assertEqual(qa.summarize([])["listing_rows"],0)
