import pathlib
import sys
import unittest
from datetime import date, timedelta
from urllib.parse import quote

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import radar_agenda_adapters as ad
import radar_definitivo as rd

class CulturalAgendaAdapterTests(unittest.TestCase):
    def test_alternativa_multiple_sessions_per_day(self):
        today=date.today()+timedelta(days=2)
        tomorrow=today+timedelta(days=1)
        d1=today.strftime("%d/%m/%Y")
        d2=tomorrow.strftime("%d/%m/%Y")
        html=f"""<h1>Play</h1><p>Av. 51 entre 9 y 10<br>
          Entrada: $ 10.000,00 - Viernes - 19:30 hs y 20:30 hs - {d1}
          <br>Entrada: $ 10.000,00 - Sábado - 19:30 hs y 20:30 hs - {d2}</p>"""
        out=ad.extract_listings(html,"https://www.alternativateatral.com/obra103606-play")
        self.assertEqual(len(out),4)
        self.assertEqual({x["event_time"] for x in out},{"19:30","20:30"})
        self.assertEqual({x["event_date"] for x in out},{today.isoformat(),tomorrow.isoformat()})
        self.assertTrue(all(x["review_state"]=="observed_unverified" for x in out))

    def test_casa_metro_explicit_spanish_date_and_venue(self):
        when=date.today()+timedelta(days=9)
        month=list(ad.MONTHS)[0]  # month text below built using inverse map
        month=next(k for k,v in ad.MONTHS.items() if v==when.month)
        text=f"""<main><h1>Sofía Calvo | Es hora de hablar</h1>
             <p>Fecha: {month} {when.day:02d}, {when.year}</p>
             <p>Hora de inicio: 19:00</p>
             <p>Lugar: Sala C - Casa Metro</p><p>Coordenadas: Calle 4</p></main>"""
        got=ad.extract_listings(text,"https://casametro.com.ar/evento/sofia-calvo/")
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["venue"],"Sala C - Casa Metro")
        self.assertEqual(got[0]["event_time"],"19:00")

    def test_opera_original_program_listing_date_without_fake_hour(self):
        when=date.today()+timedelta(days=10)
        html=f"""<section><h2>Carmen Sánchez Viamonte en el Teatro Ópera LP</h2>
             <ul><li>{when.strftime("%d/%m/%Y")}</li><li>La Plata</li></ul>Comprar Tickets
             <h2>Luz Gaggi en el Teatro Ópera LP</h2><ul>
             <li>{(when+timedelta(days=1)).strftime("%d/%m/%Y")}</li></ul></section>"""
        got=ad.extract_listings(html,"https://operalp.com.ar/agenda/")
        self.assertEqual(len(got),2)
        self.assertEqual(got[0]["event_time"],None)
        self.assertEqual(got[0]["evidence_tier"],"primary_program")

    def test_genda_scoped_listing_and_secondary_status(self):
        d=date.today()+timedelta(days=1)
        html="""<p>Teatro</p><p>Play, de Samuel Beckett</p>
              <p><i></i>19:30 hs | <i></i>Teatro Argentino</p>
              <p>Gratis Cine</p><p>Otra película</p><p>20:30 hs | Cine Select</p>"""
        url="https://agendalaplata.ar/?fecha="+d.isoformat()
        got=ad.extract_listings(html,url)
        self.assertEqual(len(got),2)
        self.assertEqual({x["event_time"] for x in got},{"19:30","20:30"})
        self.assertTrue(all(x["evidence_tier"]=="secondary_agenda" for x in got))
        self.assertEqual(ad.extract_listings(html,"https://agendalaplata.ar/"),[])

    def test_special_links_genda_and_opera_no_host_escape(self):
        d=date.today()+timedelta(days=1)
        html=f'<a href="/?fecha={d.isoformat()}">Día</a><a href="https://evil.example/?fecha={d.isoformat()}">Malo</a>'
        src="https://agendalaplata.ar/"
        links=ad.special_links(src,rd.parse_html(html))
        self.assertEqual(len(links),1)
        self.assertEqual(links[0][0],"https://agendalaplata.ar/?fecha="+d.isoformat())
        opera=rd.parse_html('<a href="https://livepass.com.ar/events/carmen-en-opera">Comprar</a>')
        self.assertEqual(len(ad.special_links("https://operalp.com.ar/agenda/",opera)),1)

    def test_validated_query_parameters_lumen_artis(self):
        u=rd.safe_public_link("?p=2907&post_type=funcion&utm_source=untrusted","https://lumenartis.org/")
        self.assertEqual(u,"https://lumenartis.org/?p=2907&post_type=funcion")

    def test_genda_source_scan_fetches_date_pages_without_accepting_events(self):
        d=date.today()+timedelta(days=1)
        root="https://agendalaplata.ar/"
        day=root+"?fecha="+d.isoformat()
        class Budget:
            def can_fetch(self,url): return url in (root,day)
            def request(self,url):
                if url==root:
                    return 200,f'<a href="/?fecha={d.isoformat()}">Agenda</a>',None
                return 200,"<p>Cine</p><p>Función de prueba</p><p>20:00 hs | Cine Select</p>",None
        source=dict(source_id="genda",url=root,source_role="secondary_agenda",seed_urls=[])
        check,candidates=rd.scan_source(source,Budget(),"full")
        self.assertEqual(check["status"],"ok")
        self.assertTrue(any(x["title"]=="Función de prueba" for x in check["_listings"]))
        self.assertGreaterEqual(check["details_opened"],1)

    def test_stale_event_is_not_accepted_as_listing(self):
        got=ad.extract_listings(
            '<h1>Obra</h1><p>Entrada: $ 2.000,00 - Viernes - 19:30 hs - 12/10/2024</p>',
            "https://www.alternativateatral.com/obra101-old")
        self.assertEqual(got,[])

if __name__=="__main__":
    unittest.main()
