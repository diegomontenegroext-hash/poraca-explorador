"""Independent positive and negative controls for evidence-derived source territory."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'radar2'))
from territory import event_location, VERSION


def event(city, region='Buenos Aires', postal=None, lat=None, lon=None):
    address={'@type':'PostalAddress','addressLocality':city,
             'addressRegion':region, 'addressCountry':'AR'}
    if postal:address['postalCode']=postal
    place={'@type':'Place','name':'Sala del evento','address':address}
    if lat is not None:place['geo']={'latitude':lat,'longitude':lon}
    return {'@type':'Event', 'name':'Función de prueba',
            'url':'https://www.eventbrite.com.ar/e/evento-123',
            'location':place}


class JsonLdTerritoryTests(unittest.TestCase):
    def test_city_bell_remains_local_when_region_is_generic_province(self):
        result=event_location(event('City Bell','Buenos Aires','B1896'))
        self.assertEqual(result['status'],'source_stated_local')
        self.assertEqual(result['area'],'La Plata y alrededores')
        self.assertFalse(result['editorial_approved'])

    def test_caba_region_and_postcode(self):
        for item in (
            event('Villa Ortuzar','Cdad. Autónoma de Buenos Aires','C1427'),
            event('Buenos Aires','Cdad. Autónoma de Buenos Aires','C1414'),
            event('San Nicolás','CABA','C1041'),
            event('Ciudad Autónoma de Buenos Aires','Buenos Aires','C1020'),
        ):
            with self.subTest(item=item['location']['address']):
                result=event_location(item)
                self.assertEqual(result['status'],'source_stated_outside')
                self.assertEqual(result['area'],'CABA')
                self.assertTrue(result['source_url'].startswith('https://'))

    def test_buenos_aires_without_specific_region_needs_postal_or_geo(self):
        self.assertEqual(event_location(event('Buenos Aires'))['status'],'pending')
        self.assertEqual(event_location(event('Buenos Aires','',None,-34.5881906,-58.3835406))['status'],'source_stated_outside')
        self.assertEqual(event_location(event('Buenos Aires','',None,-34.9,-58.5))['status'],'pending')

    def test_account_and_search_page_do_not_establish_location(self):
        item={'@type':'Event','name':'Teatro UNLP presenta una función'}
        result=event_location(item,'https://www.eventbrite.com.ar/b/argentina--la-plata/')
        self.assertEqual(result['status'],'pending')
        self.assertNotIn('area',result)
        self.assertEqual(result['version'],VERSION)

    def test_contradictory_address_stays_pending(self):
        self.assertEqual(event_location(event('City Bell','CABA','C1020'))['status'],'pending')

    def test_venue_name_alone_is_not_geography(self):
        item={'url':'https://www.eventbrite.com.ar/e/123',
              'location':{'name':'Teatro Argentino de La Plata'}}
        self.assertEqual(event_location(item)['status'],'pending')

    def test_country_and_url_handling(self):
        item=event('Montevideo','Montevideo')
        item['location']['address']['addressCountry']='UY'
        item['url']='http://not-secure.example.net'
        result=event_location(item,'https://www.eventbrite.com.ar/e/example')
        self.assertEqual(result['status'],'source_stated_outside')
        self.assertEqual(result['source_url'],'https://www.eventbrite.com.ar/e/example')
        self.assertFalse(result['editorial_approved'])


if __name__ == '__main__':
    unittest.main()
