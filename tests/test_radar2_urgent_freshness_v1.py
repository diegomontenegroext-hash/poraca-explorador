"""Bounded priority refresh selection and persistence guardrails; no live network."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'radar2'))
import source_cadence
from persist import SQL

class NearTermRefreshTests(unittest.TestCase):
 def test_selection_limits_hosts_and_blocks_unsafe_urls(self):
  rows=[
   {'url':'https://pogo.ar/evento/a','source':'pogo.ar','first_event_date':'2026-11-07'},
   {'url':'https://pogo.ar/evento/b','source':'pogo.ar','first_event_date':'2026-11-07'},
   {'url':'http://unsafe.example.org/item','source':'unsafe','first_event_date':'2026-11-07'},
   {'url':'https://127.0.0.1/internal','source':'private','first_event_date':'2026-11-07'},
   {'url':'https://www.instagram.com/p/abc','source':'Instagram','first_event_date':'2026-11-07'},
   {'url':'https://www.passline.com/eventos/1','source':'www.passline.com','first_event_date':'2026-11-08'},
   {'url':'https://festival.freezer.com.ar/programacion','source':'festival.freezer.com.ar','first_event_date':'2026-11-08'},
   {'url':'https://www.eventbrite.com.ar/e/test','source':'www.eventbrite.com.ar','first_event_date':'2026-11-09'}
  ]
  guarded=SimpleNamespace(safe_url=lambda u:urlsplit(u).hostname not in ('127.0.0.1','localhost'))
  with patch.dict(sys.modules,{'capabilities':guarded}):
   with patch.object(source_cadence,'execute',return_value={'rows':rows}) as fake:
    selected=source_cadence.urgent_source_rechecks('dummy',limit=3)
    self.assertEqual([x['source'] for x in selected],
                     ['pogo.ar','www.passline.com','festival.freezer.com.ar'])
    self.assertEqual(len(selected),3)
    self.assertEqual(fake.call_count,1)
    self.assertEqual(len(source_cadence.urgent_source_rechecks('dummy',limit=90)),3)

 def test_sql_is_bounded_and_focuses_on_existing_upcoming_origins(self):
  sql=source_cadence.URGENT_REFRESH_SQL
  for fragment in (
   "FROM radar2.proposals p",
   "JOIN radar2.documents d",
   "AT TIME ZONE 'America/Argentina/Buenos_Aires'",
   "p.event_date BETWEEN",
   "::date + 14",
   "priority_original DESC",
   "d.source='festival.freezer.com.ar'",
   "d.source='www.passline.com'",
   "d.fetched_at<now()-interval '36 hours'",
   "p.last_seen_at<now()-interval '24 hours'",
   "d.fetched_at<now()-interval '12 hours'",
   "p.review_state<>'historico'",
   "p.event_time>to_char",
   "OR p.event_time IS NULL",
   "p.event_date>(now() AT TIME ZONE",
   "LIMIT 18"):
   self.assertIn(fragment,sql)
  self.assertNotIn('INSERT',sql.upper())
  self.assertNotIn('UPDATE',sql.upper())
  self.assertIn("d.fetched_at<now()-interval '36 hours'",sql)
  self.assertIn('LIMIT 18',sql)
  self.assertNotIn("::date + 7",sql)
  # The live 8/11 SELECT now includes 21/11 Joystick (freshness overdue),
  # while the runner still hard-caps actual HTTP checks to three origins.

 def test_persist_keeps_earlier_explicit_editorial_decisions(self):
  self.assertIn("'category_revision'",SQL)
  self.assertIn("'territory_revision'",SQL)
  self.assertIn("'editorial_exclusion'",SQL)
  self.assertIn("THEN radar2.proposals.category",SQL)
  self.assertIn("THEN 'historico' ELSE excluded.review_state",SQL)
  self.assertIn("AND NOT (excluded.evidence ? k)",SQL)

 def test_existing_incremental_only_and_receipts(self):
  code=(ROOT/'radar2/actions_pilot.py').read_text()
  self.assertIn("if not corrective:",code)
  self.assertIn("urgent_source_rechecks(conn,limit=3)",code)
  self.assertIn("'urgent_source_refresh':urgent_refresh",code)
  self.assertIn("c.fetch(item['url'],item['source'])",code)
  self.assertIn("extract_document(c,d,accounts,'near_term_source_refresh_v1')",code)
  self.assertIn("if not full:",code)

if __name__=='__main__':
 unittest.main()
