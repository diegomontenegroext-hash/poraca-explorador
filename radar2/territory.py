"""Evidence-bound geographic scope for *individual* structured event locations.

This classifies the location claimed by a primary event page, NOT its publisher,
the city used in a search query, or the location of an Instagram account.
It never makes an editorial publication decision.
"""
import re
import unicodedata
from urllib.parse import urlsplit

VERSION = 'territory-jsonld-v1'
LOCALITIES = {
    'la plata', 'city bell', 'manuel b gonnet', 'gonnet', 'tolosa',
    'villa elisa', 'berisso', 'ensenada', 'punta lara',
    'gorina', 'los hornos', 'melchor romero', 'abasto',
    'ringuelet', 'hernandez', 'arturo segui', 'lisandro olmos'
}
CABA_LOCALITIES = {
    'ciudad autonoma de buenos aires', 'caba', 'capital federal',
    'villa ortuzar', 'san nicolas', 'palermo', 'recoleta',
    'monserrat', 'balvanera', 'belgrano', 'retiro'
}


def normalized(value):
    return re.sub(r'\s+', ' ', ''.join(
        c for c in unicodedata.normalize('NFKD', str(value or '').lower())
        if not unicodedata.combining(c))).strip()


def https_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return None
    parsed = urlsplit(value)
    return value if parsed.scheme == 'https' and parsed.netloc and not parsed.username else None


def event_location(item, fallback_url=None):
    """Source-stated geography, never 'independently verified'.

    Unknown / contradictory geography stays pending; no blanket decisions based
    on the publication domain or on the fact that the search was for La Plata.
    """
    location = (item or {}).get('location') or {}
    if isinstance(location, list):
        location = next((x for x in location if isinstance(x, dict)), {})
    if not isinstance(location, dict):
        location = {}
    address = location.get('address') or {}
    if isinstance(address, list):
        address = next((x for x in address if isinstance(x, dict)), {})
    if not isinstance(address, dict):
        address = {}
    locality = str(address.get('addressLocality') or '').strip()
    region = str(address.get('addressRegion') or '').strip()
    country = address.get('addressCountry') or ''
    if isinstance(country, dict):
        country = country.get('name') or country.get('identifier') or ''
    country_norm = normalized(country)
    postal = str(address.get('postalCode') or '').strip()
    city = normalized(locality)
    province = normalized(region)
    geo = location.get('geo') or {}
    if not isinstance(geo, dict):
        geo = {}
    try:
        lat = float(geo.get('latitude'))
        lon = float(geo.get('longitude'))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            lat = lon = None
    except (TypeError, ValueError, OverflowError):
        lat = lon = None

    url = https_url((item or {}).get('url')) or https_url(fallback_url)
    base = {
        'version': VERSION,
        'status': 'pending',
        'locality': locality or None,
        'region': region or None,
        'postal_code': postal or None,
        'country': str(country).strip() or None,
        'venue': str(location.get('name') or '').strip() or None,
        'source_url': url,
        'basis': 'insufficient_or_conflicting_structured_location',
        'original_preserved': True,
        'editorial_approved': False,
    }
    # Missing country is not license to infer the city. An explicitly
    # non-Argentine address is outside the local region.
    if country_norm and country_norm not in ('ar', 'argentina'):
        base.update(status='source_stated_outside',basis='jsonld_country_outside_argentina')
        return base

    local_claim = city in LOCALITIES
    caba_claim = city in CABA_LOCALITIES or (
        'ciudad autonoma de buenos aires' in province or province == 'caba')
    # The address's precise postal code or coordinate is *supporting evidence*,
    # not an invented venue inferred from the account or from the query URL.
    caba_postal = bool(re.fullmatch(r'C1\d{3}[A-Z]{0,3}', postal.upper()))
    caba_inner_geo = (lat is not None and
                      -34.67 <= lat <= -34.54 and -58.53 <= lon <= -58.34)
    if local_claim and (caba_claim or caba_postal or caba_inner_geo):
        # An internally contradictory primary source is not evidence of a
        # confirmed local event. Preserve it for a human locality check.
        base.update(status='pending',basis='conflicting_structured_location')
    elif local_claim:
        base.update(status='source_stated_local',basis='jsonld_address_locality',
                    area='La Plata y alrededores')
    elif caba_claim and not local_claim:
        base.update(status='source_stated_outside',basis='jsonld_caba_locality_or_region',
                    area='CABA')
    elif (city in ('buenos aires', 'buenos aires capital federal', '') and
          not local_claim and (caba_postal or (city == 'buenos aires' and caba_inner_geo))):
        base.update(status='source_stated_outside',
                    basis='jsonld_caba_postal_or_inner_geo',
                    area='CABA')
    return base
