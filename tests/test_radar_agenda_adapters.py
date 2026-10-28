import pathlib
import sys
import unittest
from unittest.mock import patch
from collections import Counter
from datetime import date, timedelta, datetime
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

    def test_genda_rotates_distant_days_without_missing_near_days(self):
        day=date.today()
        dates=[day+timedelta(days=i) for i in range(20)]
        html="".join('<a href="/?fecha='+d.isoformat()+'">Día</a>' for d in dates)
        page=rd.parse_html(html)
        a=ad.special_links("https://agendalaplata.ar/",page,
                           at=datetime(day.year,day.month,day.day,9))
        b=ad.special_links("https://agendalaplata.ar/",page,
                           at=datetime(day.year,day.month,day.day,17))
        self.assertEqual(len(a),5)
        self.assertEqual(len(b),5)
        self.assertTrue(a[0][0].endswith(day.isoformat()))
        self.assertTrue(a[1][0].endswith((day+timedelta(days=1)).isoformat()))
        self.assertNotEqual([u for u,_ in a],[u for u,_ in b])

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

    def test_jsonld_graph_multiple_sessions_local_time(self):
        when=date.today()+timedelta(days=3)
        payload='{"@context":"https://schema.org","@graph":[{"@type":"Event","name":"Teatro documento","startDate":"'+when.isoformat()+'T22:30:00Z","location":{"@type":"Place","name":"Sala experimental"}},{"@type":"MusicEvent","name":"Otra función","startDate":"'+when.isoformat()+'","location":{"name":"Teatro Centro"}}]}'
        html='<script type="application/ld+json">'+payload+'</script>'
        got=ad.extract_listings(html,"https://agendalaplata.ar/?fecha="+when.isoformat())
        self.assertEqual(len(got),2)
        self.assertEqual(got[0]["event_time"],"19:30")
        self.assertEqual(got[1]["event_time"],None)
        self.assertTrue(all(g["review_state"]=="observed_unverified" for g in got))

    def test_opera_heading_segments_beyond_700_and_official_ticket_link(self):
        d=date.today()+timedelta(days=4)
        link="https://livepass.com.ar/events/esquina-libertad-en-el-opera-lp"
        # Real Elementor templates contain several wrappers between headings.
        html=('<section><h2>Esquina Libertad en el Teatro Ópera LP</h2>'
              + '<div class="elementor-container">'*12
              + ('<span class="event-decoration">Información artística</span>'*30)
              + '<li>'+d.strftime("%d/%m/%Y")+'</li>'
              + '<a href="'+link+'">Comprar Tickets</a></section>')
        got=ad.extract_listings(html,"https://operalp.com.ar/agenda/")
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["event_date"],d.isoformat())
        self.assertEqual(got[0]["event_time"],None)
        self.assertEqual(got[0]["proof_url"],link)

    def test_genda_date_render_fallback_when_http_has_empty_shell(self):
        d=date.today()+timedelta(days=1)
        root="https://agendalaplata.ar/"
        day=root+"?fecha="+d.isoformat()
        class Budget:
            total=0
            by_host=Counter()
            def remaining(self):return 95
            def can_fetch(self,url):return url in (root,day)
            def request(self,url):
                if url==root:
                    return 200,'<a href="/?fecha='+d.isoformat()+'">Calendario</a>',None
                return 200,'<html><body>Trayendo la cartelera...</body></html>',None
        browser_html='Cine\nFunción demostración de Genda\n20:00 hs | Cine Select\n+ Info\nAvisame'
        source=dict(source_id="genda",url=root,source_role="secondary_agenda",seed_urls=[])
        with patch.object(rd,"render_date_pages",return_value=({day:browser_html},None)) as render:
            check,candidates=rd.scan_source(source,Budget(),"full")
        self.assertEqual(check["_genda_render_pages"],1)
        self.assertTrue(any(v["title"]=="Función demostración de Genda" for v in check["_listings"]))
        self.assertEqual(check["_listings"][0]["evidence_tier"],"secondary_agenda")
        render.assert_called_once()

    def test_genda_visible_text_with_real_card_sequence(self):
        d=date.today()+timedelta(days=1)
        text="""Qué hacer en La Plata
Teatro
HAMLET...No quiero morir
15:00 hs | Escuela de Teatro La Plata
+ Info
Avisame!
¿Con quién irías?
Cine
Éramos tan flacos - Dir. Carlos Castro
18:30 hs | Cine Select (Espacio INCAA)
+ Info
Música En vivo Espectáculo
Kevin - Liniers: Eternotour
20:00 hs | Teatro Metro
+ Info
"""
        got=ad.extract_listings(text,"https://agendalaplata.ar/?fecha="+d.isoformat())
        self.assertEqual(len(got),3)
        self.assertEqual(got[0]["title"],"HAMLET...No quiero morir")
        self.assertEqual(got[1]["venue"],"Cine Select (Espacio INCAA)")
        self.assertEqual(got[2]["event_time"],"20:00")

    def test_genda_venue_split_across_visible_lines(self):
        when=date.today()+timedelta(days=2)
        visible="Teatro\nPlay, de Samuel Beckett\n19:30 hs\n|\nTeatro Argentino\n+ Info\n"
        records=ad.extract_listings(visible,"https://agendalaplata.ar/?fecha="+when.isoformat())
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]["venue"],"Teatro Argentino")

    def test_browser_scope_rejects_unknown_urls_and_future_dates(self):
        from radar_genda_browser import validated_date_pages
        d=date.today()+timedelta(days=1)
        base="https://agendalaplata.ar/?fecha="+d.isoformat()
        urls=[base,"https://evil.example/?fecha="+d.isoformat(),
              "https://agendalaplata.ar/admin?fecha="+d.isoformat(),
              "https://agendalaplata.ar/?fecha=2040-02-10",
              "https://agendalaplata.ar/?fecha=not-a-date"]
        self.assertEqual(validated_date_pages(urls,today=date.today()),[base])

    def test_metro_official_ticket_date_not_box_office_hours(self):
        d=date.today()+timedelta(days=2)
        month=next(k for k,v in ad.MONTHS.items() if v==d.month)
        html=('<section><h2>Kevin Johanse + Liniers</h2>'
              '<p><strong>Día/s y horario/s:</strong><small>Jueves, '
              +str(d.day)+' de '+month.title()+' de '+str(d.year)
              +' . 21:00 hs.</small></p>'
              '<p>Horarios de atención: lunes a sábados 10:00 a 19:00 hs</p></section>')
        url="https://www.teatrometrolp.com.ar/entrada/kevin-johanse-liniers-100884"
        got=ad.extract_listings(html,url)
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["event_date"],d.isoformat())
        self.assertEqual(got[0]["event_time"],"21:00")
        self.assertEqual(got[0]["venue"],"Teatro Metro")
        self.assertEqual(got[0]["proof_url"],url)

    def test_metro_index_multiple_shows_exact_dates_and_hours(self):
        d=date.today()+timedelta(days=2)
        d2=d+timedelta(days=1)
        html=('<h3>Kevin Johanse + Liniers</h3><p>Descripción...</p><p>Jueves, '
              +d.strftime("%d/%m/%Y")+' - 21:00 hs.</p>'
              +'<h3>Juli Bellese</h3><p>'+d2.strftime("%d/%m/%Y")
              +' - 21:00 hs.</p>')
        got=ad.extract_listings(html,"https://www.teatrometrolp.com.ar/entradas/cartelera/")
        self.assertEqual(len(got),2)
        self.assertEqual({x["event_date"] for x in got},{d.isoformat(),d2.isoformat()})
        self.assertTrue(all(x["proof_url"].endswith("/entradas/cartelera/") for x in got))

    def test_argentino_official_event_date_not_booking_date(self):
        d=date.today()+timedelta(days=4)
        html=('<p>SALA Astor Piazzolla</p><p>Obra teatral “Mi vida anterior” '
              'de Teresa Donato y Dennis Smith | Domingo 1/11 | 19:00</p>'
              '<p>Inicio de adquisición 22/10/2026 12:00:00</p>'
              '<p>Fecha del evento '+d.strftime("%d/%m/%Y")+' 19:00:00</p>'
              '<p>Cierre de adquisición '+d.strftime("%d/%m/%Y")+' 19:00:00</p>')
        url="https://teatroargentino.gba.gob.ar/meet/93"
        got=ad.extract_listings(html,url)
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["event_date"],d.isoformat())
        self.assertEqual(got[0]["event_time"],"19:00")
        self.assertIn("Astor Piazzolla",got[0]["venue"])
        self.assertIn("Mi vida anterior",got[0]["title"])

    def test_argentino_concert_keeps_person_not_generic_concierto(self):
        d=date.today()+timedelta(days=4)
        html=('<p>SALA Alberto Ginastera</p>'
              '<p>Concierto | Horacio Lavandera y Cuarteto de la UNNOBA | Martes 3/11 | 19:30</p>'
              '<p>Fecha del evento '+d.strftime("%d/%m/%Y")+' 19:30:00</p>')
        got=ad.extract_listings(html,"https://teatroargentino.gba.gob.ar/meet/97")
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["title"],"Horacio Lavandera y Cuarteto de la UNNOBA")

    def test_lumen_official_prose_date_and_original_title(self):
        d=date.today()+timedelta(days=4)
        month=next(k for k,v in ad.MONTHS.items() if v==d.month)
        html=('<article><p>El <strong>domingo '+str(d.day)+' de '+month
              +' a las 18 h</strong>, el Teatro recibirá a Novo Ensamble, '
              'que presentará <em>El dúo de La Africana</em>, una zarzuela.</p></article>')
        url="https://lumenartis.org/?p=2907&post_type=funcion"
        got=ad.extract_listings(html,url)
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["title"],"El dúo de La Africana")
        self.assertEqual(got[0]["event_date"],d.isoformat())
        self.assertEqual(got[0]["event_time"],"18:00")
        self.assertEqual(got[0]["evidence_tier"],"primary_venue")

    def test_argentino_nested_html_and_booking_windows(self):
        d=date.today()+timedelta(days=7)
        html=('<html><body><ul><li><p>Programación</p></li></ul>'
              '<p>SALA Alberto Ginastera</p>'
              '<p><span>Concierto | Horacio Lavandera y Cuarteto de la UNNOBA '
              '| Martes 3/11 | 19:30</span></p>'
              '<p>Inicio de adquisición 02/10/2026 11:00:00</p>'
              '<div><p><strong>Fecha del evento</strong> '
              +d.strftime("%d/%m/%Y")+' 19:30:00</p></div>'
              '</body></html>')
        got=ad.extract_listings(html,"https://teatroargentino.gba.gob.ar/meet/97")
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["title"],"Horacio Lavandera y Cuarteto de la UNNOBA")
        self.assertIn("Ginastera",got[0]["venue"])

    def test_lumen_nav_paragraph_before_real_article(self):
        d=date.today()+timedelta(days=5)
        month=next(k for k,v in ad.MONTHS.items() if v==d.month)
        html=('<html><head><title>El dúo de La Africana – Teatro de Cámara</title></head>'
              '<body><p>Asociate y contactanos</p><nav><p>Programación</p></nav>'
              '<article><p>El <strong>domingo '+str(d.day)+' de '+month+
              ' a las 18 h</strong>, el Teatro recibirá a Novo Ensamble, '
              'que presentará <em>El dúo de La Africana</em>, una zarzuela.</p>'
              '</article></body></html>')
        got=ad.extract_listings(html,"https://lumenartis.org/?p=2907&post_type=funcion")
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["title"],"El dúo de La Africana")
        self.assertEqual(got[0]["event_date"],d.isoformat())

    def test_argentino_browser_fallback_when_http_only_has_shell(self):
        d=date.today()+timedelta(days=6)
        root="https://teatroargentino.gba.gob.ar/"
        detail="https://teatroargentino.gba.gob.ar/meet/93"
        class Budget:
            total=0
            by_host=Counter()
            def can_fetch(self,u):return u in (root,detail)
            def remaining(self):return 95
            def request(self,u):
                return (200,"<p>Programación general</p>",None) if u==root else (
                    200,"<html><title>Teatro Argentino</title><body>Cargando...</body></html>",None)
        rendered=('<p>SALA Astor Piazzolla</p>'
            '<p>Obra teatral “Mi vida anterior” de Teresa Donato y Dennis Smith | Domingo 1/11 | 19:00</p>'
            '<p>Fecha del evento '+d.strftime("%d/%m/%Y")+' 19:00:00</p>')
        source=dict(source_id="argentino",url=root,source_role="primary_venue",
                    seed_urls=[detail])
        with patch.object(rd,"render_argentino_event_pages",
                          return_value=({detail:rendered},None)) as browser:
            check,records=rd.scan_source(source,Budget(),"incremental")
        self.assertEqual(len(check["_listings"]),1)
        self.assertEqual(check["_listings"][0]["event_date"],d.isoformat())
        browser.assert_called_once()

    def test_lumen_no_date_or_no_emphasis_not_a_structured_event(self):
        html='<article><p>Una presentación de nuestra asociación cultural.</p></article>'
        self.assertEqual(ad.extract_listings(html,
           "https://lumenartis.org/?p=2907&post_type=funcion"),[])

    @unittest.skipUnless(date.today().month==10,"October monthly screening regression")
    def test_select_ecoselect_monthly_secondary_screenings(self):
        html=('<h1>Octubre en Cine Select</h1>'
              '<p>Jueves 29 de octubre 18:30 — Espacio INCAA (entrada $5000): '
              'Éramos tan flacos / Dir. Carlos Castro / Argentina / 2025</p>'
              '<p>Jueves 29 de octubre 20:30 — Misa Nocturna (entrada $5000): Scream / Dir. Wes Craven</p>'
              '<p>Viernes 12 de septiembre 20:00 — archivo fuera del mes</p>')
        got=ad.extract_listings(html,"https://agendadecine.com/ciclos-y-festivales/octubre-en-cine-select")
        self.assertEqual(len(got),2)
        self.assertEqual({x["event_time"] for x in got},{"18:30","20:30"})
        self.assertTrue(all(x["venue"]=="Cine Select (Espacio INCAA)" for x in got))
        self.assertTrue(all(x["evidence_tier"]=="secondary_cinema_agenda" for x in got))
        ec=ad.extract_listings(html.replace("Cine Select","Cine Ecoselect"),
                              "https://agendadecine.com/ciclos-y-festivales/octubre-en-cine-ecoselect")
        self.assertEqual(len(ec),2)
        self.assertTrue(all(x["venue"]=="Cine Ecoselect (Espacio INCAA)" for x in ec))

    def test_stale_event_is_not_accepted_as_listing(self):
        got=ad.extract_listings(
            '<h1>Obra</h1><p>Entrada: $ 2.000,00 - Viernes - 19:30 hs - 12/10/2024</p>',
            "https://www.alternativateatral.com/obra101-old")
        self.assertEqual(got,[])

if __name__=="__main__":
    unittest.main()
