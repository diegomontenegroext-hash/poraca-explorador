import pathlib
import sys
import unittest
from datetime import date,timedelta

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_adaptive_discovery import discover_sections
import radar_definitivo as rd
from radar_agenda_adapters import extract_listings


class AdaptiveDiscoveryTests(unittest.TestCase):
    def test_new_unknown_source_no_special_domain(self):
        root="https://cultura-ejemplo.org/"
        html=('''<a href="/contacto/">Contacto</a>
            <a href="/agenda/">Agenda cultural</a>
            <a href="/talleres/">Talleres</a>
            <a href="/cartelera/">Cartelera</a>
            <a href="/agenda/">Agenda otra vez</a>
            <a href="https://evil.example/eventos/">Eventos falsos</a>''')
        result=discover_sections(root,rd.parse_html(html).links)
        self.assertEqual([x[0] for x in result],[
            root+"agenda/",root+"cartelera/",root+"talleres/"])
        self.assertEqual(len(result),3)
        self.assertTrue(all(x[1]=="adaptive_section_link" for x in result))

    def test_format_change_reuses_generic_signal(self):
        root="https://nuevo-espacio.org/"
        old=rd.parse_html('<a href="/calendario/">Calendario</a>').links
        new=rd.parse_html('<a href="/programacion/">Programación</a>').links
        self.assertEqual(discover_sections(root,old)[0][0],root+"calendario/")
        self.assertEqual(discover_sections(root,new)[0][0],root+"programacion/")

    def test_disallow_external_query_nonaudience_and_multilevel(self):
        root="https://nuevo-espacio.org/"
        html=('''<a href="/agenda/?date=2026">Agenda</a>
          <a href="/agenda/privada/">Agenda privada</a>
          <a href="https://nuevo-espacio.org:8443/agenda/">Agenda puerto</a>
          <a href="http://nuevo-espacio.org/agenda/">HTTP</a>
          <a href="//evil.example/agenda/">Agenda otra host</a>
          <a href="/contacto/">Contacto</a>''')
        self.assertEqual(discover_sections(root,rd.parse_html(html).links),[])

    def test_generic_schema_without_primary_claims(self):
        day=(date.today()+timedelta(days=7)).isoformat()
        raw=('''<script type="application/ld+json">'''
          + '{"@type":"Event","name":"Feria de arte en barrio",'
          + '"startDate":"'+day+'T18:30:00-03:00",'
          + '"location":{"name":"Sala Barrial"}}'
          + '''</script>''')
        got=extract_listings(raw,"https://fuente-nueva.org/agenda/")
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["event_time"],"18:30")
        self.assertEqual(got[0]["evidence_tier"],"structured_origin_unverified")
        self.assertEqual(got[0]["review_state"],"observed_unverified")

    def test_unknown_site_without_date_does_not_create_event(self):
        page='<h1>Talleres y Yoga</h1><p>Todos los jueves a las 18</p>'
        self.assertEqual(extract_listings(page,"https://fuente-nueva.org/"),[])

    def test_scan_source_uses_real_menu_fallback_and_no_fake_candidates(self):
        root="https://fuente-nueva.org/"
        page=root+"agenda/"
        day=(date.today()+timedelta(days=5)).isoformat()
        detail=('''<script type="application/ld+json">'''
                + '{"@type":"Event","name":"Concierto de prueba barrial",'
                + '"startDate":"'+day+'T20:30:00-03:00",'
                + '"location":{"name":"Sala Barrial"}}'
                + '''</script>''')
        class Budget:
            def __init__(self):
                self.calls=[]
                self.pages={root:(200,'<a href="/agenda/">Agenda</a>',None),
                            page:(200,detail,None)}
            def can_fetch(self,url):return url in self.pages
            def request(self,url):
                self.calls.append(url)
                return self.pages[url]
            def remaining(self):return 100
        b=Budget()
        check,candidates=rd.scan_source({"source_id":"new","url":root},b,"full")
        self.assertEqual(b.calls,[root,page])
        self.assertEqual(check["details_opened"],1)
        self.assertEqual(len(check["_listings"]),1)
        self.assertEqual(check["_listings"][0]["evidence_tier"],"structured_origin_unverified")
        self.assertEqual(candidates,[])
        self.assertEqual(check["status"],"ok")

    def test_index_without_event_is_not_successful_extraction(self):
        root="https://nueva-fuente.org/"
        page=root+"agenda/"
        class Budget:
            def can_fetch(self,url):return True
            def request(self,url):
                return (200,('<a href="/agenda/">Agenda</a>' if url==root
                            else '<h1>Agenda sin fechas</h1>'),None)
            def remaining(self):return 100
        check,candidates=rd.scan_source({"source_id":"new","url":root},Budget(),"full")
        self.assertEqual(check["status"],"index_only")
        self.assertEqual(check["details_opened"],1)
        self.assertEqual(candidates,[])
        self.assertEqual(check["_listings"],[])

if __name__=="__main__":unittest.main()
