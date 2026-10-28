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
    def test_alpedo_rendered_dated_cards_are_secondary_and_individual(self):
        day=date.today()+timedelta(days=1)
        month=next(k for k,v in ad.MONTHS.items() if v==day.month)
        raw=(f'<p>{month.capitalize()} {day.year}</p>'
             '<h6>Parque Ecológico</h6><p>07:00 a 19:00</p>'
             '<p>Parque Ecológico</p>'
             '<h6>Taller de hongos comestibles</h6>'
             '<p>16:00</p><p><i></i>Facultad de Ciencias Naturales - UNLP</p>'
             '<h6>Mugre + Terrores Nocturnos</h6>'
             '<p>20:00</p><p><i></i>Ciudad de Gatos</p>'
             '<h6>Kevin - Liniers: Eternotour</h6>'
             '<p>20:00</p><p>Teatro Metro</p>'
             '<h6>República de los Niños</h6>'
             '<p>07:00 / 22:00</p><p>República de los Niños</p>')
        url="https://alpedo.ar/?fecha="+day.isoformat()
        items=ad.extract_listings(raw,url)
        self.assertEqual(len(items),3)
        self.assertEqual({x["title"] for x in items},{
            "Taller de hongos comestibles",
            "Mugre + Terrores Nocturnos",
            "Kevin - Liniers: Eternotour"})
        self.assertTrue(all(x["event_date"]==day.isoformat() for x in items))
        self.assertTrue(all(x["evidence_tier"]=="secondary_agenda" for x in items))
        self.assertEqual(next(x for x in items if x["title"].startswith("Mugre"))["venue"],
                         "Ciudad de Gatos")

    def test_alpedo_rejects_stale_date_or_unscoped_root(self):
        day=date.today()+timedelta(days=1)
        wrongmonth=next(k for k,v in ad.MONTHS.items()
                        if v==(day.month%12)+1)
        raw=f"<p>{wrongmonth} {day.year}</p><h6>Concierto</h6><p>21:00</p><p>Club</p>"
        url="https://alpedo.ar/?fecha="+day.isoformat()
        self.assertEqual(ad.extract_listings(raw,url),[])
        self.assertEqual(ad.extract_listings(raw,"https://alpedo.ar/"),[])
        self.assertEqual(ad.extract_listings(raw,
            "https://alpedo.ar/?cinema=1&fecha="+day.isoformat()),[])
        self.assertEqual(ad.extract_listings(raw,
            "https://evil.example/?fecha="+day.isoformat()),[])

    def test_alpedo_skip_finalized_or_undated_spa_index(self):
        day=date.today()+timedelta(days=2)
        month=next(k for k,v in ad.MONTHS.items() if v==day.month)
        raw=(f'<p>{month} {day.year}</p>'
             '<h6>Evento futuro</h6><p>19:00</p><p>Centro Cultural</p>'
             '<div>Finalizadas</div>'
             '<h6>Actividad ya realizada</h6><p>18:00</p><p>Otra sede</p>')
        names=[x["title"] for x in ad.extract_listings(raw,
                           "https://alpedo.ar/?fecha="+day.isoformat())]
        self.assertIn("Evento futuro",names)
        self.assertNotIn("Actividad ya realizada",names)

    def test_alpedo_jsonld_mirror_never_becomes_primary(self):
        day=date.today()+timedelta(days=1)
        month=next(k for k,v in ad.MONTHS.items() if v==day.month)
        raw=(f'<p>{month} {day.year}</p>'
             '<script type="application/ld+json">'
             '{"@type":"MusicEvent","name":"Festival ajeno",'
             '"startDate":"'+day.isoformat()+'T20:00:00-03:00",'
             '"location":{"name":"Sala declarada por tercero"}}'
             '</script>')
        url="https://alpedo.ar/?fecha="+day.isoformat()
        res=ad.extract_listings(raw,url)
        self.assertEqual(len(res),1)
        self.assertEqual(res[0]["evidence_tier"],"secondary_agenda")
        self.assertEqual(res[0]["review_state"],"observed_unverified")

    def test_alpedo_realistic_last_session_before_finalizadas(self):
        # Shape from the real dated agenda: a one-clock upcoming card
        # is immediately followed by the archive header and older clocks.
        when=date.today()+timedelta(days=1)
        month=next(k for k,v in ad.MONTHS.items() if v==when.month)
        html=(f"<p>{month.capitalize()} {when.year}</p>"
            "<p>20:00 a 22:00</p><h6>República de los Niños</h6>"
            "<p>07:00 a 22:00</p><p>República de los Niños</p>"
            "<h6>Arctic Monkeys - AM</h6><p>20:00</p>"
            "<p>Bocanada Bar</p>"
            "<h6>Cantobar - Karaoke</h6><p>21:00</p>"
            "<p>Teatro Bar Cultural La Ferretería</p>"
            "<p><i>Finalizadas</i></p>"
            "<h6>Actividad de ayer</h6><p>10:00</p>"
            "<p>Centro Cultural de archivo</p>")
        url="https://alpedo.ar/?fecha="+when.isoformat()
        events=ad.extract_listings(html,url)
        names=[x["title"] for x in events]
        self.assertEqual(set(names),{"Arctic Monkeys - AM","Cantobar - Karaoke"})
        self.assertEqual(len(events),2)
        self.assertNotIn("Actividad de ayer",names)
        self.assertEqual(events[-1]["event_time"],"21:00")
        self.assertEqual(events[-1]["venue"],
            "Teatro Bar Cultural La Ferretería")

    def test_alpedo_never_leaks_partial_img_div_into_venue(self):
        day=date.today()+timedelta(days=1)
        month=next(k for k,v in ad.MONTHS.items() if v==day.month)
        # Regression from actual first FULL, where 49 of 70 venues
        # ended in '<div class="img-thumb-container ...' because the
        # old regex could remove complete tags but not partial ones.
        raw=(f"<p>{month} {day.year}</p>"
             '<h6>La marcha sobre Roma (Dir. Dino Risi)</h6>'
             '<p>17:30</p><p><i></i>Teatro Bar Cultural La Ferretería</p>'
             '<div class="img-thumb-container '+('rounded '*300)
             +'<h6>¿Sueñan las plantas con poemas?</h6>'
             '<p>18:00</p><p><i></i>Museo Almafuerte</p>')
        rows=ad.extract_listings(raw,"https://alpedo.ar/?fecha="+day.isoformat())
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["venue"],"Teatro Bar Cultural La Ferretería")
        self.assertEqual(rows[1]["venue"],"Museo Almafuerte")
        self.assertTrue(all("<" not in x["venue"] for x in rows))

    def test_alpedo_ignores_inline_javascript_after_last_venue(self):
        day=date.today()+timedelta(days=1)
        month=next(k for k,v in ad.MONTHS.items() if v==day.month)
        raw=(f"<p>{month} {day.year}</p>"
             '<h6>Cantamos fatal</h6><p>21:00</p>'
             '<p><i></i>Ciudad de Gatos</p>'
             '<script>var tooltipTriggerList = [].slice.call(document.querySelectorAll("a"));</script>'
             '</body>')
        res=ad.extract_listings(raw,"https://alpedo.ar/?fecha="+day.isoformat())
        self.assertEqual(len(res),1)
        self.assertEqual(res[0]["venue"],"Ciudad de Gatos")

    def test_alpedo_browser_redirect_must_preserve_exact_day(self):
        from radar_genda_browser import matches_alpedo_date_response
        target="https://alpedo.ar/?fecha=2026-10-29"
        self.assertTrue(matches_alpedo_date_response(
            target,"https://www.alpedo.ar/?fecha=2026-10-29"))
        for wrong in (
            "https://alpedo.ar/",
            "https://alpedo.ar/?fecha=2026-10-28",
            "https://alpedo.ar/?fecha=2026-10-29&utm_source=cache",
            "http://alpedo.ar/?fecha=2026-10-29",
            "https://evil.example/?fecha=2026-10-29",
            "https://alpedo.ar:8443/?fecha=2026-10-29",
            "https://alpedo.ar/eventos/?fecha=2026-10-29",
        ):
            with self.subTest(wrong=wrong):
                self.assertFalse(matches_alpedo_date_response(target,wrong))

    def test_alpedo_real_rendered_dom_has_p_wrapped_title_and_clock_after_p(self):
        when=date.today()+timedelta(days=1)
        month=next(k for k,v in ad.MONTHS.items() if v==when.month)
        # The real dated HTML has title nested inside P, clock in a raw
        # text sibling, then a venue P containing an icon, not a table.
        raw=(f"<body><p>{month.capitalize()} {when.year}</p>"
             "<p><h6>Parque Ecológico</h6></p>"
             "07:00     a 19:00"
             "<p><i></i> Parque Ecológico</p>"
             "<p><h6>HAMLET...No quiero morir</h6></p>"
             "15:00"
             "<p><i></i> Escuela de Teatro La Plata</p>"
             "<p><h6>Mugre + Terrores Nocturnos</h6></p>"
             "20:00"
             "<p><i></i> Ciudad de Gatos</p>"
             "</body>")
        url="https://alpedo.ar/?fecha="+when.isoformat()
        rows=ad.extract_listings(raw,url)
        self.assertEqual([(x["title"],x["event_time"],x["venue"]) for x in rows],[
            ("HAMLET...No quiero morir","15:00","Escuela de Teatro La Plata"),
            ("Mugre + Terrores Nocturnos","20:00","Ciudad de Gatos")])
        self.assertTrue(all(x["evidence_tier"]=="secondary_agenda" for x in rows))

    def test_alpedo_browser_dates_allow_only_same_site_and_four_day_horizon(self):
        from radar_genda_browser import validated_alpedo_date_pages
        today=date(2026,10,28)
        urls=[
            "https://alpedo.ar/?fecha=2026-10-28",
            "https://alpedo.ar/?fecha=2026-10-29",
            "https://alpedo.ar/?fecha=2026-10-29",
            "https://alpedo.ar/?fecha=2026-11-07",
            "https://alpedo.ar/?cinema=1&fecha=2026-10-30",
            "https://evil.example/?fecha=2026-10-30",
            "https://alpedo.ar/?fecha=2026-10-31",
        ]
        self.assertEqual(validated_alpedo_date_pages(urls,today=today),[
            "https://alpedo.ar/?fecha=2026-10-28",
            "https://alpedo.ar/?fecha=2026-10-29",
            "https://alpedo.ar/?fecha=2026-10-31"])

    def test_alpedo_fallback_keeps_running_if_root_gains_generic_links(self):
        today=rd.datetime.now(rd.timezone.utc).astimezone(
            rd.ZoneInfo("America/Argentina/Buenos_Aires")).date()
        month=next(k for k,v in ad.MONTHS.items() if v==today.month)
        dated="https://alpedo.ar/?fecha="+today.isoformat()
        markup=(f"<p>{month} {today.year}</p>"
                "<h6>Reunión cultural</h6><p>19:30</p>"
                "<p>Centro Cultural Local</p>")
        budget=rd.Budget(seconds=100)
        budget.request=lambda url:(200,"<html><p>Menu visible</p></html>",None)
        src={"source_id":"rd-web-cb094233",
             "source_role":"secondary_agenda","url":"https://alpedo.ar/"}
        # An irrelevant menu item is not an event, and should not
        # suppress reading the date-specific calendar.
        with patch.object(rd,"links_from_page",
                          return_value=[("https://alpedo.ar/informacion/","Menu")]):
            with patch.object(rd,"render_alpedo_date_pages",
                              return_value=({dated:markup},None)) as browser:
                check,candidates=rd.scan_source(src,budget,"full")
        browser.assert_called_once()
        self.assertEqual(check["status"],"ok")
        self.assertEqual(len(check["_listings"]),1)
        self.assertEqual(check["_listings"][0]["title"],"Reunión cultural")

    def test_alpedo_browser_recovery_after_index_only_http(self):
        today=rd.datetime.now(rd.timezone.utc).astimezone(
            rd.ZoneInfo("America/Argentina/Buenos_Aires")).date()
        month=next(k for k,v in ad.MONTHS.items() if v==today.month)
        dated="https://alpedo.ar/?fecha="+today.isoformat()
        html=(f"<p>{month} {today.year}</p>"
              "<h6>Taller de literatura</h6>"
              "<p>19:00</p><p>Café de las artes</p>")
        budget=rd.Budget(seconds=100)
        budget.request=lambda url:(200,"<html><p>Agenda</p></html>",None)
        src={"source_id":"rd-web-cb094233",
             "source_role":"secondary_agenda","url":"https://alpedo.ar/"}
        with patch.object(rd,"render_alpedo_date_pages",
                          return_value=({dated:html},None)) as browser:
            check,candidates=rd.scan_source(src,budget,"full")
        browser.assert_called_once()
        self.assertEqual(check["status"],"ok")
        self.assertEqual(check["_alpedo_render_pages"],1)
        self.assertEqual(len(check["_listings"]),1)
        self.assertEqual(check["_listings"][0]["venue"],"Café de las artes")
        self.assertEqual(check["_listings"][0]["evidence_tier"],"secondary_agenda")
        self.assertEqual(candidates,[])

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

    def test_alternativa_current_venue_not_historical_venue(self):
        # Regression: the original page can carry the 2026 current
        # room followed by "Histórico de funciones" with a PAST room and
        # expired/fictitious dates. Neither should leak into the agenda.
        days=(4-date.today().weekday())%7 or 7
        current=date.today()+timedelta(days=days)
        fake=current+timedelta(days=8)
        html=(
            '<h1>Las del Lirio. Tullido retrato familiar</h1>'
            '<div>CENTRO CULTURAL VIEJO ALMACEN EL OBRERO</div>'
            '<div>Av 13 1900 esquina 71 La Plata</div>'
            '<p>Viernes - 21:30 hs - Hasta el '+current.strftime("%d/%m/%Y")+'</p>'
            '<div>1 Histórico de funciones</div>'
            '<p>EN ESO ESTAMOS<br>Calle 62 e/1 y 115</p>'
            '<p>Entrada: 21:00 hs - '+fake.strftime("%d/%m/%Y")+'</p>')
        url=("https://www.alternativateatral.com/"
             "obra102973-las-del-lirio-tullido-retrato-familiar")
        got=ad.extract_listings(html,url)
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["event_date"],current.isoformat())
        self.assertEqual(got[0]["event_time"],"21:30")
        self.assertEqual(got[0]["venue"],"CENTRO CULTURAL VIEJO ALMACEN EL OBRERO")
        self.assertNotIn(fake.isoformat(),{x["event_date"] for x in got})

    def test_alternativa_historical_only_is_not_current_program(self):
        when=date.today()+timedelta(days=3)
        html=('<h1>Programa de archivo</h1>'
            '<div>1 Histórico de funciones</div>'
            '<p>EN ESO ESTAMOS<br>Calle 62 e/1 y 115</p>'
            '<p>Entrada: 21:00 hs - '+when.strftime("%d/%m/%Y")+'</p>')
        url="https://www.alternativateatral.com/obra102973-programa-archivo"
        self.assertEqual(ad.extract_listings(html,url),[])

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

    def test_casa_metro_detail_discovery_prioritizes_and_rotates(self):
        base="https://casametro.com.ar/categoria-producto/casa-metro/"
        links="".join(
            '<a href="https://casametro.com.ar/evento/show-'+str(i)+'/">'
            'Evento '+str(i)+'</a>' for i in range(1,13))
        links += (
            '<a href="https://evil.example/evento/stolen/">Malicioso</a>'
            '<a href="https://casametro.com.ar/evento/show-1/">Duplicado</a>'
            '<a href="https://casametro.com.ar/mi-cuenta">No es evento</a>'
            '<a href="https://casametro.com.ar/evento/show-1/?bad=1">Con query</a>')
        page=rd.parse_html(links)
        d=date(2026,10,28)
        run1=ad.special_links(base,page,at=datetime(2026,10,28,5))
        run2=ad.special_links(base,page,at=datetime(2026,10,28,13))
        self.assertEqual(len(run1),6)
        self.assertEqual(len({u for u,_ in run1}),6)
        self.assertEqual([u for u,_ in run1[:3]],
            ['https://casametro.com.ar/evento/show-'+str(i)+'/'
             for i in range(1,4)])
        self.assertEqual([u for u,_ in run1[:3]],
                         [u for u,_ in run2[:3]])
        self.assertNotEqual([u for u,_ in run1[3:]],
                            [u for u,_ in run2[3:]])
        self.assertTrue(all(u.startswith("https://casametro.com.ar/evento/")
                            and "?" not in u for u,_ in run1))
        self.assertEqual(ad.special_links("https://example.com/",page),[])

    def test_casa_metro_discovery_short_cardset_no_duplicates(self):
        base="https://casametro.com.ar/categoria-producto/casa-metro/"
        page=rd.parse_html(
            '<a href="/evento/primero/">Uno</a>'
            '<a href="/evento/segundo/">Dos</a>'
            '<a href="/evento/primero/">Uno de nuevo</a>'
            '<a href="//evil.example/evento/third/">Ignorar</a>')
        got=ad.special_links(base,page,at=datetime(2026,10,28,9))
        self.assertEqual([u for u,_ in got],
            ["https://casametro.com.ar/evento/primero/",
             "https://casametro.com.ar/evento/segundo/"])

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

    def test_metro_official_pagination_only_existing_source_link(self):
        root="https://www.teatrometrolp.com.ar/entradas/cartelera/"
        page=rd.parse_html(
            '<a href="/entradas/cartelera/1/?anio=&mes=">Siguiente</a>'
            '<a href="https://evil.example/entradas/cartelera/2/">Falso</a>'
            '<a href="/entradas/cartelera/2/?token=secret">No permitido</a>'
            '<a href="/entradas/cartelera/1/?anio=&mes=">Repetido</a>'
        )
        links=ad.special_links(root,page)
        self.assertEqual(links,[
            ("https://www.teatrometrolp.com.ar/entradas/cartelera/1/",
             "cartelera oficial, pagina 1")])
        self.assertEqual(ad.special_links(root,rd.parse_html(
            '<a href="https://evil.example/entradas/cartelera/1/">Falso</a>')),[])
        self.assertEqual(ad.special_links(
            "https://www.teatrometrolp.com.ar/entradas/cartelera/1/",page),[])

    def test_metro_second_page_individual_sessions_and_no_boxoffice_clock(self):
        d=date.today()+timedelta(days=20)
        d2=d+timedelta(days=21)
        html=(
            '<h3>Lisandro Aristimuño - Experiencia Coral</h3>'
            '<p>'+d.strftime("%d/%m/%Y")+' - 20:00 hs.</p>'
            '<h3>Pan con Manteca</h3><p>'
            +d2.strftime("%d/%m/%Y")+' - 21:00 hs.</p>'
            '<p>Horarios de atencion: lunes a sabados de 10 a 19 hs.</p>'
        )
        url="https://www.teatrometrolp.com.ar/entradas/cartelera/1/"
        got=ad.extract_listings(html,url)
        self.assertEqual(len(got),2)
        self.assertEqual({x["event_time"] for x in got},{"20:00","21:00"})
        self.assertEqual({x["proof_url"] for x in got},{url})
        self.assertTrue(all(x["review_state"]=="observed_unverified"
                            and x["evidence_tier"]=="primary_program"
                            for x in got))
        # La fecha de boleteria no debe generar una tercera funcion.
        self.assertEqual(ad.extract_listings(
            '<p>Horarios de atención 10:00 a 19:00</p>',url),[])

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

    def test_argentino_real_browser_div_headlines_three_schedules(self):
        # Renderer actually has no relevant <p> elements around captions;
        # the weekday/date/hour and exact Fecha del evento remain visible.
        cases=(
            ("93","Obra teatral “Mi vida anterior” de Teresa Donato y Dennis Smith",
             "Domingo",date(2026,11,1),"19:00","Mi vida anterior","Astor Piazzolla"),
            ("97","Concierto | Horacio Lavandera y Cuarteto de la UNNOBA",
             "Martes",date(2026,11,3),"19:30","Horacio Lavandera","Alberto Ginastera"),
            ("98","Masterclass | “Seamos realistas, soñemos lo imposible” con Nacha Guevara",
             "Viernes",date(2026,11,13),"20:00","Nacha Guevara","Astor Piazzolla"),
        )
        for identifier,title,weekday,when,clock,expected,room in cases:
            with self.subTest(event=identifier):
                markup=('<html><body><div>Inicio</div><div>SALA '+room+'</div>'
                        '<div>'+title+' | '+weekday+' '+str(when.day)+'/'+str(when.month)
                        +' | '+clock+'</div>'
                        '<div>Inicio de adquisición 22/10/2026 12:00:00</div>'
                        '<div>Fecha del evento '+when.strftime("%d/%m/%Y")
                        +' '+clock+':00</div></body></html>')
                rows=ad.extract_listings(markup,
                    "https://teatroargentino.gba.gob.ar/meet/"+identifier)
                self.assertEqual(len(rows),1)
                self.assertIn(expected,rows[0]["title"])
                self.assertEqual(rows[0]["event_date"],when.isoformat())
                self.assertEqual(rows[0]["event_time"],clock)
                self.assertIn(room,rows[0]["venue"])

    def test_argentino_browser_does_not_leak_sidebar_into_title(self):
        d=date(2026,11,1)
        markup=('<div>Inicio</div><div>el teatro Historia Salas TEMPORADA '
                'SALA Astor Piazzolla Obra teatral “Mi vida anterior” '
                'de Teresa Donato y Dennis Smith | Domingo 1/11 | 19:00</div>'
                '<div>Fecha del evento 01/11/2026 19:00:00</div>')
        rows=ad.extract_listings(markup,"https://teatroargentino.gba.gob.ar/meet/93")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["title"],
                         'Obra teatral “Mi vida anterior” de Teresa Donato y Dennis Smith')
        self.assertNotIn("Historia Salas",rows[0]["title"])

    def test_argentino_header_conflict_is_not_promoted(self):
        html=('<div>SALA Astor Piazzolla</div>'
              '<div>Concierto | Músicos de prueba | Viernes 13/11 | 20:00</div>'
              '<div>Fecha del evento 13/11/2026 21:00:00</div>')
        rows=ad.extract_listings(html,"https://teatroargentino.gba.gob.ar/meet/1098")
        self.assertEqual(rows,[])

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

    def test_alternativa_original_venue_from_real_page(self):
        # Source HTML published with a room followed by street address.
        url="https://www.alternativateatral.com/obra102155-cuadrilateros-6-teatro-breve-reunido"
        html=('<h1>Cuadriláteros 6, teatro breve reunido</h1>'
              '<p>Clasificaciones: Teatro, Presencial, Adultos</p>'
              '<p>TEATRO ESTUDIO DE LAS ARTES<br/>Calle 3 N 386 e/ 39 y 40 (mapa)<br/>'
              'La Plata - Buenos Aires - Argentina<br/>'
              'Entrada: $ 20.000,00 - Viernes - 22:30 hs - 30/10/2026</p>')
        with patch.object(ad,"active_date",return_value=True):
            records=ad.extract_listings(html,url)
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]["venue"],"TEATRO ESTUDIO DE LAS ARTES")
        self.assertEqual(records[0]["event_date"],"2026-10-30")

    def test_alternativa_room_from_flattened_html(self):
        html=('<h1>Epifanía</h1><div>La Plata: ESCENARIO-40 '
              'Calle 40 #1180</div><p>Viernes - 21:30 hs - 30/10/2026</p>')
        with patch.object(ad,"active_date",return_value=True):
            records=ad.extract_listings(html,
                "https://www.alternativateatral.com/obra102876-epifania")
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]["venue"],"ESCENARIO-40")

    def test_alternativa_hasta_day_does_not_invent_recurring_sessions(self):
        url="https://www.alternativateatral.com/obra103415-el-animo"
        html=('<h1>El Ánimo</h1><p>EN ESO ESTAMOS<br/>Calle 62 No. 274 e/ 1 y 115'
              '<br/>Domingo - 21:00 hs - Hasta el 01/11/2026<br/>'
              'Viernes - 21:00 hs - Hasta el 06/11/2026 y 27/11/2026</p>')
        with patch.object(ad,"active_date",return_value=True):
            got=ad.extract_listings(html,url)
        self.assertEqual({x["event_date"] for x in got},
                         {"2026-11-01","2026-11-06","2026-11-27"})
        self.assertTrue(all(x["venue"]=="EN ESO ESTAMOS" for x in got))
        self.assertTrue(all(x["event_time"]=="21:00" for x in got))
        self.assertFalse(any(x["event_date"]=="2026-11-13" for x in got))

    def test_alternativa_explict_date_without_entrada(self):
        html=('<h1>Epifanía</h1>'
              '<p>ESCENARIO-40<br/>Calle 40 #1180 (mapa)<br/>'
              'Viernes - 21:30 hs - 30/10/2026</p>')
        with patch.object(ad,"active_date",return_value=True):
            got=ad.extract_listings(html,
                "https://www.alternativateatral.com/obra102876-epifania")
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["venue"],"ESCENARIO-40")
        self.assertEqual(got[0]["event_date"],"2026-10-30")

    def test_alternativa_no_recurring_expansion_for_bad_weekday(self):
        html=('<h1>Evento</h1><p>SALA DE TEATRO<br/>Calle 30 No 800<br/>'
              'Lunes - 19:00 hs - Hasta el 30/10/2026</p>')
        with patch.object(ad,"active_date",return_value=True):
            self.assertEqual(ad.extract_listings(html,
                "https://www.alternativateatral.com/obra10001-evento"),[])
    
    def test_casa_metro_official_category_cards_keep_dates_scoped(self):
        url="https://casametro.com.ar/categoria-producto/casa-metro/"
        markup=(
            '<ul class="products">'
            '<li class="product"><span>Fecha:octubre 31, 2026</span>'
            '<span>Horario: 20:00 - 00:00</span><span>Casa Metro</span>'
            '<h2>Música como en casa – Segundo tiempo sexteto</h2></li>'
            '<li class="product"><span>Fecha:noviembre 01, 2026</span>'
            '<span>Horario: 19:00 - 00:00</span><span>Casa Metro</span>'
            '<h2>Sofía Calvo | Es hora de hablar</h2></li>'
            '<li class="product"><span>Casa Metro</span>'
            '<h2>Sin fecha visible</h2></li>'
            '</ul>')
        rows=ad.extract_listings(markup,url)
        self.assertEqual(len(rows),2)
        self.assertEqual(
            [(r["title"],r["event_date"],r["event_time"]) for r in rows],
            [("Música como en casa – Segundo tiempo sexteto","2026-10-31","20:00"),
             ("Sofía Calvo | Es hora de hablar","2026-11-01","19:00")])
        self.assertTrue(all(r["proof_url"]==url for r in rows))
        self.assertTrue(all(r["evidence_tier"]=="primary_program" for r in rows))
        self.assertTrue(all(r["review_state"]=="observed_unverified" for r in rows))

    def test_casa_metro_category_rejects_missing_time_and_mismatched_card(self):
        url="https://casametro.com.ar/categoria-producto/casa-metro/"
        markup=(
            '<li class="product"><h2>Concierto sin hora</h2>'
            '<span>Fecha:octubre 31, 2026</span><span>Casa Metro</span></li>'
            '<li class="product"><h2>Concierto sin fecha</h2>'
            '<span>Horario: 21:00 - 00:00</span><span>Casa Metro</span></li>'
            '<li class="product"><h2>Sin sede impresa</h2>'
            '<span>Fecha:octubre 31, 2026</span><span>Horario: 22:00</span></li>')
        self.assertEqual(ad.extract_listings(markup,url),[])

    def test_fcnym_unlp_official_lecture_from_published_prose(self):
        url=("https://www.fcnym.unlp.edu.ar/novedades/"
             "leccion-magistral-emilio-custodio-sobre-aguas-subterraneas-en-fcnym/")
        markup=(
            '<script type="application/ld+json">'
            '{"@type":"NewsArticle","datePublished":"2026-10-23T20:48:59+00:00"}'
            '</script><main><h1>“Lección Magistral Emilio Custodio”'
            ' sobre aguas subterráneas en FCNYM</h1><p>'
            'La Lección será dictada por el Dr. Jesús Carrera:'
            ' miércoles 18 de noviembre a las 10 horas en el '
            'Auditorio de Planta Baja de la Facultad de Ciencias Naturales '
            'y Museo. La conferencia se transmitirá por YOUTUBE.</p></main>')
        rows=ad.extract_listings(markup,url)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["event_date"],"2026-11-18")
        self.assertEqual(rows[0]["event_time"],"10:00")
        self.assertIn("Lección Magistral Emilio Custodio",rows[0]["title"])
        self.assertEqual(rows[0]["review_state"],"observed_unverified")
        self.assertEqual(rows[0]["evidence_tier"],"primary_organizer")

    def test_fcnym_unlp_lecture_rejects_missing_or_wrong_year_evidence(self):
        url=("https://www.fcnym.unlp.edu.ar/novedades/"
             "leccion-magistral-emilio-custodio-sobre-aguas-subterraneas-en-fcnym/")
        body=('<main><h1>Lección Magistral Emilio Custodio</h1><p>'
              'miércoles 18 de noviembre a las 10 horas en el Auditorio '
              'de Planta Baja de la Facultad de Ciencias Naturales y Museo'
              '</p><p>Copyright 2026</p></main>')
        self.assertEqual(ad.extract_listings(body,url),[])
        wrong=('<time datetime="2025-10-23T11:00:00"></time>'+body)
        self.assertEqual(ad.extract_listings(wrong,url),[])
        self.assertEqual(ad.extract_listings(
            '<time datetime="2026-10-23"></time>'+body,
            "https://example.com/otro-evento"),[])

    def test_gritos_official_festival_range_one_umbrella_no_invented_sessions(self):
        url="https://gritos.planetario.unlp.edu.ar/2026/index.html"
        markup=("<h1>GRITOS en el planetario</h1>"
                "<h2>Festival Internacional de Cine de Horror de La Plata</h2>"
                "<h3>V Edición - 2026 -</h3>"
                "<p>Del 30/OCT al 1/NOV 2026</p>"
                "<p>Tres días bajo el domo del Planetario de la Universidad Nacional</p>")
        rows=ad.extract_listings(markup,url)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["event_date"],"2026-10-30")
        self.assertIsNone(rows[0]["event_time"])
        self.assertEqual(rows[0]["venue"],"Planetario UNLP · Paseo del Bosque")
        self.assertEqual(rows[0]["proof_url"],url)
        self.assertEqual(rows[0]["review_state"],"observed_unverified")
        self.assertEqual(rows[0]["evidence_tier"],"primary_program")
        self.assertEqual(rows[0]["method"],"gritos_festival_official_date_range_start")

    def test_gritos_festival_prose_range_no_inferred_screenings(self):
        url="https://gritos.planetario.unlp.edu.ar/2026/index.html"
        markup=("<h1>GRITOS en el planetario</h1>"
                "<h2>Festival Internacional de Cine de Horror de La Plata</h2>"
                "<h3>V Edición - 2026 -</h3>"
                "<p>El festival se desarrollará entre los días 30 de octubre "
                "y 1 de noviembre de 2026 en el Planetario de la UNLP</p>")
        rows=ad.extract_listings(markup,url)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["event_date"],"2026-10-30")
        self.assertIsNone(rows[0]["event_time"])

    def test_gritos_does_not_infer_from_edition_year_without_range(self):
        url="https://gritos.planetario.unlp.edu.ar/2026/index.html"
        markup=("<h1>Festival Internacional de Cine de Horror</h1>"
                "<p>V Edición - 2026 - Planetario UNLP</p>"
                "<p>30/OCT al 1/NOV pero sin año explícito en el rango</p>")
        self.assertEqual(ad.extract_listings(markup,url),[])
        self.assertEqual(ad.extract_listings(markup,
            "https://example.com/2026/index.html"),[])

    def test_edita_official_home_has_two_dates_no_hours(self):
        html=('<h1>#EDITA2026 #10AÑOS</h1><p>EDITA: 5 y 6 de diciembre</p>'
              '<p>La Feria de Editoriales más importante de la región con '
              'más de 150 editoriales. Frente al Museo Provincial Emilio '
              'Pettoruti, avenida 51 entre 5 y 6, La Plata.</p>')
        with patch.object(ad,"active_date",return_value=True):
            got=ad.extract_listings(html,"https://feriaedita.com.ar/")
        self.assertEqual([x["event_date"] for x in got],
                         ["2026-12-05","2026-12-06"])
        self.assertTrue(all(x["event_time"] is None for x in got))
        self.assertTrue(all(x["evidence_tier"]=="primary_program" for x in got))

    def test_edita_missing_year_marker_does_not_guess_year(self):
        html=('<p>EDITA: 5 y 6 de diciembre</p>'
              '<p>La Plata, Frente al Museo Pettoruti</p>')
        self.assertEqual(ad.extract_listings(html,"https://feriaedita.com.ar/"),[])
    def test_stale_event_is_not_accepted_as_listing(self):
        got=ad.extract_listings(
            '<h1>Obra</h1><p>Entrada: $ 2.000,00 - Viernes - 19:30 hs - 12/10/2024</p>',
            "https://www.alternativateatral.com/obra101-old")
        self.assertEqual(got,[])

if __name__=="__main__":
    unittest.main()
