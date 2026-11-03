import pathlib
import sys
import unittest
from datetime import date
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
import radar_agenda_adapters as ad

URL="https://biblioteca.example.edu.ar/feria-de-editoriales-noctambula/"
ROOT="https://biblioteca.example.edu.ar/"
ANNOUNCEMENT=(
    "El sábado 14 de noviembre, de 19 a 24 h, la Biblioteca Pública "
    "de la Universidad Nacional de La Plata realizará la tercera edición "
    "de NOCTÁMBULA, en el marco de Museos a la Luz de la Luna 2026."
)

def article(paragraph=ANNOUNCEMENT,headline="Feria de editoriales Noctámbula",
            published="2026-11-02",outside_contact=True):
    publication=(
        '<meta property="article:published_time" '
        'content="'+published+'T10:00:00-03:00">'
    ) if published else ""
    footer=('<footer><h2>CONTACTO</h2><p>Horario de Atención al público '
            'Lunes a Viernes de 8:00 a 19:00h</p>'
            '<p>Plaza Rocha N° 137 - La Plata, Argentina</p></footer>'
            if outside_contact else "")
    return ('<html><head>'+publication+'</head><body>'
           '<article><h1>'+headline+'</h1><p>'+paragraph+'</p></article>'
           +footer+'</body></html>')


class OfficialInstitutionReviewTests(unittest.TestCase):
    def test_original_noctambula_is_a_review_only_program_window(self):
        with patch.object(ad,"active_date",return_value=True):
            found=ad.extract_listings(article(),URL,
                source_role="institutional_program")
        self.assertEqual(len(found),1)
        e=found[0]
        self.assertEqual(e["title"],"Feria de editoriales Noctámbula")
        self.assertEqual(e["event_date"],"2026-11-14")
        self.assertIsNone(e["event_time"])
        self.assertIsNone(e["venue"])
        self.assertEqual(e["public_window_start"],"19:00")
        self.assertEqual(e["public_window_end"],"24:00")
        self.assertEqual(e["time_semantics"],"cycle_public_hours_not_session")
        self.assertEqual(e["year_basis"],"publication_year_weekday_correlated")
        self.assertEqual(e["publication_date"],"2026-11-02")
        self.assertEqual(e["evidence_tier"],"structured_origin_unverified")
        self.assertEqual(e["review_state"],"observed_unverified")
        self.assertFalse(e["event_time_inferred"])
        self.assertFalse(e["venue_inferred"])
        self.assertEqual(e["proof_url"],URL)

    def test_unknown_or_secondary_source_never_inherits_original(self):
        for role in (None,"secondary_specialized_agenda","curadora",
                     "first_party_ticketing","original_venue","review"):
            with patch.object(ad,"active_date",return_value=True):
                self.assertEqual(ad.extract_listings(article(),URL,source_role=role),[],role)

    def test_no_publication_no_year_from_footer_or_copyright(self):
        no_publication=article(published=False)
        no_publication=no_publication.replace('</body>','<p>Copyright 2026</p></body>')
        with patch.object(ad,"active_date",return_value=True):
            self.assertEqual(ad.extract_listings(
                no_publication,URL,source_role="institutional_program"),[])
            self.assertEqual(ad.extract_listings(
                article(published="2025-11-02"),URL,
                source_role="institutional_program"),[])

    def test_wrong_weekday_or_archive_cannot_generate_future(self):
        for text in (
             ANNOUNCEMENT.replace("sábado 14","domingo 14"),
             ANNOUNCEMENT.replace("14 de noviembre","14 de octubre"),
             ANNOUNCEMENT.replace("19 a 24 h","19 a 25 h"),
             ANNOUNCEMENT.replace("19 a 24 h","19 a 08 h")
        ):
            with patch.object(ad,"active_date",return_value=True):
                self.assertEqual(ad.extract_listings(article(paragraph=text),URL,
                    source_role="institutional_program"),[],text)
        self.assertEqual(ad.institutional_prose_review(
            article(),URL,"institutional_program",at=date(2026,12,1)),[])

    def test_open_hours_and_multiple_articles_are_not_events(self):
        # Institutional footer is never the event description or time source.
        html=article(paragraph="Horario de atención: El sábado 14 de noviembre, de 19 a 24 h.")
        with patch.object(ad,"active_date",return_value=True):
            self.assertEqual(ad.extract_listings(html,URL,
                source_role="institutional_program"),[])
        multi=article().replace('</article>', '</article><article><h1>'
            'Festival de revistas</h1><p>El sábado 14 de noviembre, de 19 a 24 h'
            '</p></article>',1)
        with patch.object(ad,"active_date",return_value=True):
            self.assertEqual(ad.extract_listings(multi,URL,
                source_role="institutional_program"),[])

    def test_no_event_name_or_no_article_is_rejected(self):
        with patch.object(ad,"active_date",return_value=True):
            self.assertEqual(ad.extract_listings(
                article(headline="Servicios de la biblioteca"),URL,
                source_role="institutional_program"),[])
            self.assertEqual(ad.extract_listings(
                article().replace('<article>','<main>').replace('</article>','</main>'),
                URL,source_role="institutional_program"),[])

    def test_no_cross_host_urls_or_made_up_year(self):
        with patch.object(ad,"active_date",return_value=True):
            for url in ("http://biblioteca.example.edu.ar/anuncio/",
                        "https://biblioteca.example.edu.ar/anuncio/?redirect=1",
                        "https://attacker@biblioteca.example.edu.ar/anuncio/"):
                self.assertEqual(ad.institutional_prose_review(
                    article(),url,"institutional_program"),[])
        # A published source is not a permission to auto-admit as a confirmed
        # individual performance or invent library venue/address.
        for record in ad.institutional_prose_review(article(),URL,
                "institutional_program",at=date(2026,11,3)):
            self.assertNotEqual(record["evidence_tier"],"primary_venue")
            self.assertIsNone(record["event_time"])
            self.assertIsNone(record["venue"])

if __name__=="__main__":
    unittest.main()
