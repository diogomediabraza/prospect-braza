"""
Scraper using OpenStreetMap Overpass API for Portuguese businesses.
pai.pt / Páginas Amarelas blocks cloud IPs via Cloudflare TLS fingerprinting,
so we use OSM Overpass (free, open, no bot protection) instead.
"""
import re
import json
import gzip as _gzip
import zlib
import urllib.request
import urllib.parse
from typing import Optional

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Map common Portuguese niche keywords to OSM tags
NICHO_TAGS = {
    "restaurante":    [("amenity", "restaurant")],
    "restaurantes":   [("amenity", "restaurant")],
    "cafe":           [("amenity", "cafe")],
    "cafes":          [("amenity", "cafe"), ("amenity", "bar")],
    "bar":            [("amenity", "bar")],
    "clinica":        [("amenity", "clinic"), ("amenity", "doctors")],
    "clinicas":       [("amenity", "clinic"), ("amenity", "doctors")],
    "dentista":       [("amenity", "dentist")],
    "dentistas":      [("amenity", "dentist")],
    "farmacia":       [("amenity", "pharmacy")],
    "farmacias":      [("amenity", "pharmacy")],
    "hospital":       [("amenity", "hospital")],
    "hotel":          [("tourism", "hotel")],
    "hoteis":         [("tourism", "hotel")],
    "imobiliaria":    [("shop", "estate_agent")],
    "imobiliarias":   [("shop", "estate_agent")],
    "ginasio":        [("leisure", "fitness_centre")],
    "ginasios":       [("leisure", "fitness_centre")],
    "padaria":        [("shop", "bakery")],
    "padarias":       [("shop", "bakery")],
    "supermercado":   [("shop", "supermarket")],
    "supermercados":  [("shop", "supermarket")],
    "cabeleireiro":   [("shop", "hairdresser")],
    "cabeleireiros":  [("shop", "hairdresser")],
    "barbearia":      [("shop", "hairdresser")],
    "barbearias":     [("shop", "hairdresser")],
    "mecanico":       [("shop", "car_repair")],
    "oficina":        [("shop", "car_repair")],
    "oficinas":       [("shop", "car_repair")],
    "advogado":       [("office", "lawyer")],
    "advogados":      [("office", "lawyer")],
    "contabilidade":  [("office", "accountant")],
    "seguradora":     [("office", "insurance")],
    "agencia":        [("office", "travel_agent")],
    "escola":         [("amenity", "school"), ("amenity", "college")],
    "escolas":        [("amenity", "school"), ("amenity", "college")],
    "pousada":        [("tourism", "guest_house")],
    "spa":            [("leisure", "spa")],
    "veterinario":    [("amenity", "veterinary")],
    "veterinarios":   [("amenity", "veterinary")],
    "optica":         [("shop", "optician")],
    "opticas":        [("shop", "optician")],
    "joalharia":      [("shop", "jewelry")],
    "joalharias":     [("shop", "jewelry")],
    "livraria":       [("shop", "books")],
    "livrarias":      [("shop", "books")],
    "tabacaria":      [("shop", "tobacco")],
    "funeraria":      [("shop", "funeral_directors")],
    "lavandaria":     [("shop", "laundry"), ("shop", "dry_cleaning")],
}


def _fetch(url: str, data: bytes = None, timeout: int = 20) -> str:
    """Simple HTTP GET/POST with decompression."""
    headers = {
        "User-Agent": "ProspectBraza/1.0 (contact@webraza.com)",
        "Accept-Encoding": "gzip, deflate",
    }
    if data:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            enc = r.headers.get("Content-Encoding", "")
            if "gzip" in enc:
                raw = _gzip.decompress(raw)
            elif "deflate" in enc:
                try:
                    raw = zlib.decompress(raw)
                except zlib.error:
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _geocode(localidade: str) -> Optional[tuple]:
    """Return (south, west, north, east) bounding box for a Portuguese locality."""
    q = urllib.parse.quote(f"{localidade}, Portugal")
    url = f"{NOMINATIM_URL}?q={q}&format=json&limit=1&countrycodes=pt"
    body = _fetch(url)
    if not body:
        return None
    try:
        results = json.loads(body)
        if results:
            bb = results[0].get("boundingbox", [])
            if len(bb) == 4:
                # Nominatim returns [south, north, west, east]
                return (float(bb[0]), float(bb[2]), float(bb[1]), float(bb[3]))
    except Exception:
        pass
    return None


def _build_query(nicho: str, bbox: tuple, limit: int) -> str:
    """Build Overpass QL query for the given niche within a bounding box."""
    s, w, n, e = bbox
    bb = f"{s},{w},{n},{e}"
    nicho_lower = nicho.lower().strip()

    # Specific OSM tags for known niches
    tags = NICHO_TAGS.get(nicho_lower, [])
    # Also try removing trailing 's' for plural forms
    if not tags and nicho_lower.endswith("s"):
        tags = NICHO_TAGS.get(nicho_lower[:-1], [])

    parts = []

    # Tag-based search (most reliable — finds all businesses of that type)
    for k, v in tags:
        parts.append(f'  node["{k}"="{v}"]["name"]({bb});')
        parts.append(f'  way["{k}"="{v}"]["name"]({bb});')

    # Name-based search (catches businesses with the keyword in their name)
    parts.append(f'  node["name"~"{nicho_lower}",i]({bb});')
    parts.append(f'  way["name"~"{nicho_lower}",i]({bb});')

    return (
        f'[out:json][timeout:25];\n'
        f'(\n'
        + "\n".join(parts) +
        f'\n);\n'
        f'out center {limit * 3};\n'
    )


def _normalize_phone(raw: str) -> str:
    """Normalize a phone number to 9 Portuguese digits."""
    if not raw:
        return ""
    cleaned = re.sub(r'[\s\-\.\(\)+]', '', raw)
    # Remove country code
    cleaned = re.sub(r'^351', '', cleaned)
    # Must be 9 digits starting with 2, 3, 6, 7, 9
    if re.match(r'^[23679]\d{8}$', cleaned):
        return cleaned
    return ""


def _clean_social_url(raw: str, platform: str) -> str:
    """Normalize a social media handle or URL to a full URL."""
    if not raw:
        return ""
    raw = raw.strip()
    bases = {
        "instagram": "https://www.instagram.com/",
        "facebook":  "https://www.facebook.com/",
        "linkedin":  "https://www.linkedin.com/company/",
    }
    if raw.startswith("http"):
        return raw
    base = bases.get(platform, "")
    handle = raw.lstrip("@")
    return f"{base}{handle}" if base and handle else raw


def _element_to_company(el: dict, nicho: str, localidade: str) -> Optional[dict]:
    """Convert an OSM element dict to a company entry."""
    tags = el.get("tags", {})
    name = tags.get("name", "").strip()
    if not name or len(name) < 2:
        return None

    phone_raw = (
        tags.get("phone") or
        tags.get("contact:phone") or
        tags.get("contact:mobile") or
        tags.get("mobile") or ""
    )
    phone = _normalize_phone(phone_raw)

    website = tags.get("website") or tags.get("contact:website") or tags.get("url") or ""
    if website and not website.startswith("http"):
        website = f"https://{website}"

    email = tags.get("email") or tags.get("contact:email") or ""

    instagram_raw = tags.get("contact:instagram") or tags.get("instagram") or ""
    instagram = _clean_social_url(instagram_raw, "instagram")

    facebook_raw = tags.get("contact:facebook") or tags.get("facebook") or ""
    facebook = _clean_social_url(facebook_raw, "facebook")

    street = tags.get("addr:street", "")
    house_nr = tags.get("addr:housenumber", "")
    city = (tags.get("addr:city", "") or
            tags.get("addr:town", "") or
            tags.get("addr:village", ""))
    parts = []
    if street:
        parts.append(f"{street} {house_nr}".strip())
    if city and city.lower() != localidade.lower():
        parts.append(city)
    morada = ", ".join(p for p in parts if p)

    codigo_postal = tags.get("addr:postcode", "")

    entry: dict = {"nome": name, "nicho": nicho, "localidade": localidade}
    if phone:
        entry["telefone"] = phone
    if email:
        entry["email"] = email
    if website:
        entry["website"] = website
    if instagram:
        entry["instagram"] = instagram
    if facebook:
        entry["facebook"] = facebook
    if morada:
        entry["morada"] = morada
    if codigo_postal:
        entry["codigo_postal"] = codigo_postal

    return entry


def scrape_paginas_amarelas(
    nicho: str,
    localidade: str,
    max_results: int = 50,
) -> list:
    """
    Search for Portuguese companies using OpenStreetMap Overpass API.
    Returns list of raw company dicts (same interface as before).
    """
    bbox = _geocode(localidade)
    if not bbox:
        return []

    query = _build_query(nicho, bbox, max_results)
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    body = _fetch(OVERPASS_URL, data=data, timeout=25)

    if not body:
        return []

    try:
        result = json.loads(body)
    except Exception:
        return []

    elements = result.get("elements", [])

    seen: set = set()
    companies: list = []

    for el in elements:
        company = _element_to_company(el, nicho, localidade)
        if not company:
            continue
        key = company["nome"].lower()
        if key in seen:
            continue
        seen.add(key)
        companies.append(company)
        if len(companies) >= max_results:
            break

    return companies


def fetch_url(url: str, timeout: int = 10, opener=None) -> str:
    """Fetch a website URL for digital presence checking."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            enc = r.headers.get("Content-Encoding", "")
            if "gzip" in enc:
                raw = _gzip.decompress(raw)
            return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def check_digital_presence(website: Optional[str]) -> dict:
    """Check basic digital presence for a company. Returns boolean flags + social media URLs."""
    _empty = {
        "tem_website": False, "tem_loja_online": False,
        "tem_gtm": False, "tem_ga4": False,
        "tem_pixel_meta": False, "tem_google_ads": False,
        "tem_facebook_ads": False,
        "tem_instagram": False, "tem_facebook": False, "tem_linkedin": False,
        "instagram": None, "facebook": None, "linkedin": None,
    }
    if not website:
        return _empty
    url = website if website.startswith("http") else f"https://{website}"
    html = fetch_url(url, timeout=10)
    if not html:
        return {**_empty, "tem_website": True}
    html_lower = html.lower()

    # Extract Instagram page URL (skip post/reel/story links)
    instagram_url = None
    ig_match = re.search(r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)/?', html)
    if ig_match and not any(x in ig_match.group(0) for x in
                            ['/p/', '/reel/', '/stories/', '/explore/', 'sharer']):
        instagram_url = ig_match.group(0).rstrip('/')

    # Extract Facebook page URL (skip share/tracker links)
    facebook_url = None
    fb_match = re.search(r'https?://(?:www\.)?facebook\.com/([A-Za-z0-9_.]+)/?', html)
    if fb_match and not any(x in fb_match.group(0) for x in
                            ['sharer', '/tr?', 'plugins', 'dialog', '/share']):
        facebook_url = fb_match.group(0).rstrip('/')

    # Extract LinkedIn company/profile URL
    linkedin_url = None
    li_match = re.search(
        r'https?://(?:www\.)?linkedin\.com/(?:company|in)/([A-Za-z0-9_-]+)/?', html
    )
    if li_match:
        linkedin_url = li_match.group(0).rstrip('/')

    return {
        "tem_website": True,
        "tem_loja_online": any(kw in html_lower for kw in
            ["woocommerce", "shopify", "cart", "carrinho", "checkout", "loja"]),
        "tem_gtm": "googletagmanager.com" in html_lower or "gtm.js" in html_lower,
        "tem_ga4": "gtag" in html_lower or "google-analytics" in html_lower or "ga4" in html_lower,
        "tem_pixel_meta": "connect.facebook.net" in html_lower or "fbq(" in html_lower,
        "tem_google_ads": "googleadservices" in html_lower or "conversion" in html_lower,
        "tem_facebook_ads": "connect.facebook.net" in html_lower,
        "tem_instagram": instagram_url is not None or "instagram.com" in html_lower,
        "tem_facebook": facebook_url is not None or "facebook.com" in html_lower,
        "tem_linkedin": linkedin_url is not None or "linkedin.com" in html_lower,
        "instagram": instagram_url,
        "facebook": facebook_url,
        "linkedin": linkedin_url,
    }


def scrape_all_sources(nicho: str, localidade: str, max_results: int = 20) -> list:
    """
    Aggregates companies from ALL free data sources:
      1. OpenStreetMap Overpass API   — always runs, no key, richest geo data
      2. Wikidata SPARQL              — always runs, no key, structured data
      3. Foursquare Places v3         — runs if FOURSQUARE_API_KEY is set
      4. HERE Places v1               — runs if HERE_API_KEY is set
      5. Google Places                — runs if GOOGLE_PLACES_KEY is set
      6. infopaginas.pt               — HTML scraping, no key (may be blocked from cloud)
      7. guiaempresa.pt               — HTML scraping, no key (may be blocked from cloud)

    Deduplicates by name (case-insensitive). When the same company appears in multiple
    sources, missing fields are merged from secondary sources.
    """
    # Lazy imports to keep source files optional
    try:
        from lib.source_wikidata import scrape_wikidata
    except Exception:
        scrape_wikidata = lambda *a, **kw: []  # noqa: E731

    try:
        from lib.source_infopaginas import scrape_infopaginas, scrape_guiaempresa
    except Exception:
        scrape_infopaginas = lambda *a, **kw: []  # noqa: E731
        scrape_guiaempresa = lambda *a, **kw: []  # noqa: E731

    try:
        from lib.source_apis import scrape_foursquare, scrape_here, scrape_google_places
    except Exception:
        scrape_foursquare = lambda *a, **kw: []  # noqa: E731
        scrape_here = lambda *a, **kw: []  # noqa: E731
        scrape_google_places = lambda *a, **kw: []  # noqa: E731

    per_source = max(max_results, 20)  # ask each source for at least 20
    all_raw: list = []

    for fn in (
        lambda: scrape_paginas_amarelas(nicho, localidade, per_source),
        lambda: scrape_wikidata(nicho, localidade, per_source),
        lambda: scrape_foursquare(nicho, localidade, per_source),
        lambda: scrape_here(nicho, localidade, per_source),
        lambda: scrape_google_places(nicho, localidade, per_source),
        lambda: scrape_infopaginas(nicho, localidade, per_source),
        lambda: scrape_guiaempresa(nicho, localidade, per_source),
    ):
        try:
            all_raw.extend(fn())
        except Exception:
            pass

    # Deduplicate by name — merge missing fields from secondary sources
    seen: dict = {}  # normalised_name → company dict
    for company in all_raw:
        name = company.get("nome", "").strip()
        if not name or len(name) < 2:
            continue
        key = name.lower()
        if key not in seen:
            seen[key] = dict(company)
        else:
            # Fill in any fields the primary source didn't have
            primary = seen[key]
            for field in ("telefone", "email", "website", "morada",
                          "codigo_postal", "instagram", "facebook", "linkedin"):
                if not primary.get(field) and company.get(field):
                    primary[field] = company[field]

    return list(seen.values())[:max_results]


def calculate_scores(data: dict) -> dict:
    """Calculate scoring for a company based on digital presence."""
    md = 0
    if data.get("tem_website"): md += 3
    if data.get("tem_instagram") or data.get("tem_facebook"): md += 2
    if data.get("tem_ga4") or data.get("tem_gtm"): md += 2
    if data.get("tem_pixel_meta") or data.get("tem_google_ads"): md += 2
    if data.get("tem_loja_online"): md += 1
    score_maturidade = min(10.0, md)

    oportunidade = 10 - score_maturidade
    if not data.get("tem_pixel_meta") and not data.get("tem_google_ads"):
        oportunidade = min(10.0, oportunidade + 2)
    score_oportunidade = round(oportunidade, 1)

    contact_score = 0
    if data.get("telefone"): contact_score += 3
    if data.get("email"): contact_score += 2

    prioridade = (score_oportunidade * 0.6 + contact_score) * (10 / 8)
    score_prioridade = min(10.0, round(prioridade, 1))

    return {
        "score_maturidade_digital": round(score_maturidade, 1),
        "score_oportunidade_comercial": score_oportunidade,
        "score_prioridade_sdr": score_prioridade,
    }
