import importlib.util
import pathlib
import unittest

p = pathlib.Path(__file__).resolve().parents[1] / "src" / "discover_post_links.py"
spec = importlib.util.spec_from_file_location("discover_post_links", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestDiscovery(unittest.TestCase):
    def test_extract_post_and_reel(self):
        body = ('<a href="https://www.instagram.com/p/DeHOPiJRwNi/">post</a>'
                '<script>"https:\/\/www.instagram.com\/reel\/DeIP5x6RTRH\/"</script>')
        urls = mod.extract_instagram_permalinks(body)
        self.assertEqual(len(urls), 2)
        self.assertIn("https://www.instagram.com/p/DeHOPiJRwNi/", urls)
        self.assertIn("https://www.instagram.com/reel/DeIP5x6RTRH/", urls)

    def test_profile_alone_not_counted(self):
        self.assertEqual(mod.extract_instagram_permalinks('<a href="https://www.instagram.com/cineselect/">perfil</a>'), [])

    def test_only_same_domain_articles_followed(self):
        page = ('<a href="/que-hago/un-evento-n555">uno</a>'
                '<a href="https://example.net/que-hago/otro">externo</a>'
                '<a href="/la-plata/otra-nota">dos</a>')
        urls = mod.candidate_article_links(page, "https://www.0221.com.ar/que-hago", 3)
        self.assertEqual(len(urls), 2)
        self.assertTrue(all(x.startswith("https://www.0221.com.ar/") for x in urls))


if __name__ == "__main__":
    unittest.main()
