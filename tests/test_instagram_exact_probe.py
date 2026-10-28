import importlib.util
import pathlib
import unittest

p = pathlib.Path(__file__).resolve().parents[1] / "src" / "instagram_exact_probe.py"
spec = importlib.util.spec_from_file_location("instagram_exact_probe", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestInstagramExact(unittest.TestCase):
    def test_only_exact_public_permalinks(self):
        self.assertTrue(all(mod.valid_exact_url(s["url"]) for s in mod.SOURCES))
        self.assertTrue(mod.valid_exact_url("https://www.instagram.com/organizador/p/Dem0abcd-/"))
        for bad in (
            "https://www.instagram.com/cineselect/",
            "https://instagram.com/stories/alguien/123/",
            "http://www.instagram.com/p/abc/",
            "https://bad.example/p/abc/",
        ):
            self.assertFalse(mod.valid_exact_url(bad))

    def test_metadata_is_not_proof_without_matching_canonical(self):
        html = '<meta property="og:description" content="Texto de la publicacion">'
        v = mod.evaluate_html(html, "https://www.instagram.com/p/DeHOPiJRwNi/")
        self.assertFalse(v["potential_post_metadata"])

    def test_exact_post_metadata_is_only_candidate(self):
        html = ('<link rel="canonical" href="https://www.instagram.com/p/DeHOPiJRwNi/">'
                '<meta property="og:description" content="Texto primario">')
        v = mod.evaluate_html(html, "https://www.instagram.com/p/DeHOPiJRwNi/")
        self.assertTrue(v["potential_post_metadata"])

    def test_no_missing_social_posts_invented(self):
        self.assertEqual(len(mod.SOURCES), 3)
        self.assertEqual(mod.MAX_BYTES, 256 * 1024)


if __name__ == "__main__":
    unittest.main()
