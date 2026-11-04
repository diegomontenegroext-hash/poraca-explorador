import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_exact_original_read_receipt import attach_exact_original_receipts as attach

URL="https://example.org/event/real-program"
HTML="<html><body><script type='application/ld+json'>"+("event-data "*20)+"</script></body></html>"
BASE={"title":"Tres bandas en una noche","event_date":"2026-11-12",
      "venue":"Sala de barrio","event_time":None,"proof_url":URL,
      "method":"schema_org_event_sessions","evidence_tier":"primary_structured_page"}

class ExactReadReceiptTests(unittest.TestCase):
    def scan(self,records=None,url=URL,body=HTML,status=200,role="original_venue"):
        return attach(records if records is not None else [BASE],url,body,status,
             source_role=role,observed_at="2026-11-04T12:00:00+00:00")

    def test_exact_direct_read_records_digest_and_optional_time(self):
        rows=self.scan()
        self.assertNotIn("_original_read_receipt",BASE)
        r=rows[0]["_original_read_receipt"]
        self.assertEqual(r["schema"],"radar-exact-original-read-v1")
        self.assertEqual(r["opened_url"],URL)
        self.assertEqual(r["extracted_fields"]["time"],None)
        self.assertEqual(len(r["document_sha256"]),64)
        self.assertEqual(r["http_status"],200)
        self.assertEqual(r["source_role"],"original_venue")
        self.assertEqual(self.scan()[0]["_original_read_receipt"]["document_sha256"],
                         r["document_sha256"])

    def test_no_receipt_when_link_not_opened_or_root(self):
        self.assertNotIn("_original_read_receipt",
                         self.scan(url="https://example.org/other")[0])
        self.assertNotIn("_original_read_receipt",
                         self.scan(url="https://example.org/")[0])
        self.assertNotIn("_original_read_receipt",
                         self.scan(url="https://example.org/agenda")[0])

    def test_failed_http_secondary_and_invalid_json_never_certify(self):
        self.assertNotIn("_original_read_receipt",self.scan(status=403)[0])
        self.assertNotIn("_original_read_receipt",self.scan(role="secondary_agenda")[0])
        self.assertNotIn("_original_read_receipt",self.scan(records=[
             dict(BASE,evidence_tier="structured_origin_unverified")])[0])
        self.assertNotIn("_original_read_receipt",self.scan(records=[
             dict(BASE,method="doblet_official_index_explicit_function")])[0])
        self.assertNotIn("_original_read_receipt",self.scan(records=[
             dict(BASE,venue="")])[0])

    def test_separate_sessions_not_merged_and_no_invented_time(self):
        other=dict(BASE,title="Otra función real")
        out=self.scan(records=[BASE,other])
        self.assertEqual(len(out),2)
        self.assertTrue(all("_original_read_receipt" in x for x in out))
        self.assertEqual([x["_original_read_receipt"]["extracted_fields"]["program"]
                          for x in out],["Tres bandas en una noche","Otra función real"])
        self.assertTrue(all(x["_original_read_receipt"]["extracted_fields"]["time"]
                            is None for x in out))

if __name__=="__main__":
    unittest.main()
