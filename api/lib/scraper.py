"""
Scraper using OpenStreetMap Overpass API for Portuguese businesses.
pai.pt / Páginas Amarelas blocks cloud IPs via Cloudflare TLS fingerprinting,
so we use OSM Overpass (free, open, no bot protection) instead.

CHANGELOG:
- calculate_scores() reescrito: escala 0-100, penalizações, confiança por campo
- classify_lead() novo: Excelente / Bom / Fraco / Lixo
- check_digital_presence() corrigido: Instagram/Facebook exigem URL real (não só menção)
- scrape_all_sources() deduplicação multi-campo (nome + telefone + domínio)
- _extract_email_quality() novo: separa email comercial de email genérico
"""
import re
import json
import gzip as _gzip
import zlib
import urllib.request
import urllib.parse
from typing import Optional

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL  = "https://overpass-api.de/api/interpreter"

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
    except Exception as e:
        print(f"[FETCH] FAILED {url[:80]}: {type(e).__name__}: {e}", flush=True)
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
                return (float(bb[0]), float(bb[2]), float(bb[1]), float(bb[3]))
    except Exception:
        pass
    return None


def _build_query(nicho: str, bbox: tuple, limit: int) -> str:
    """Build Overpass QL query for the given niche within a bounding box."""
    s, w, n, e = bbox
    bb = f"{s},{w},{n},{e}"
    nicho_lower = nicho.lower().strip()

    tags = NICHO_TAGS.get(nicho_lower, [])
    if not tags and nicho_lower.endswith("s"):
        tags = NICHO_TAGS.get(nicho_lower[:-1], [])

    parts = []
    for k, v in tags:
        parts.append(f'  node["{k}"="{v}"]["name"]({bb});')
        parts.append(f'  way["{k}"="{v}"]["name"]({bb});')

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
    cleaned = re.sub(r'^351', '', cleaned)
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


def _normalize_name_for_dedup(name: str) -> str:
    """
    Normaliza nome para deduplicação.
    Remove acentos, lowercase, remove artigos e pontuação.
    """
    import unicodedata
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower()
    name = re.sub(r'\b(o|a|os|as|de|do|da|dos|das|e|em|no|na|nos|nas|um|uma)\b', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def _extract_domain(url: str) -> str:
    """Extrai domínio de uma URL para deduplicação."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url if url.startswith("http") else f"https://{url}")
        domain = parsed.netloc.lower().replace("www.", "")
        return domain
    except Exception:
        return ""


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

    street   = tags.get("addr:street", "")
    house_nr = tags.get("addr:housenumber", "")
    city     = (tags.get("addr:city", "") or
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
    if phone:      entry["telefone"]      = phone
    if email:      entry["email"]         = email
    if website:    entry["website"]       = website
    if instagram:  entry["instagram"]     = instagram
    if facebook:   entry["facebook"]      = facebook
    if morada:     entry["morada"]        = morada
    if codigo_postal: entry["codigo_postal"] = codigo_postal

    return entry


def scrape_paginas_amarelas(nicho: str, localidade: str, max_results: int = 50) -> list:
    """Search for Portuguese companies using OpenStreetMap Overpass API."""
    bbox = _geocode(localidade)
    if not bbox:
        print(f"[OSM] Geocode failed for '{localidade}'", flush=True)
        return []

    print(f"[OSM] Geocoded '{localidade}' -> bbox={bbox}", flush=True)
    query = _build_query(nicho, bbox, max_results)
    data  = urllib.parse.urlencode({"data": query}).encode("utf-8")
    body  = _fetch(OVERPASS_URL, data=data, timeout=25)

    if not body:
        return []

    try:
        result = json.loads(body)
    except Exception as e:
        print(f"[OSM] JSON parse error: {e}", flush=True)
        return []

    elements = result.get("elements", [])
    print(f"[OSM] Got {len(elements)} elements from Overpass", flush=True)

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
        company["fonte_raw"] = "OSM Overpass"
        companies.append(company)
        if len(companies) >= max_results:
            break

    return companies


def fetch_url(url: str, timeout: int = 10) -> str:
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


# Emails de junk que não devem ser aceites (trackers, libs, domínios genéricos)
_EMAIL_JUNK = {
    'example', 'sentry', 'noreply', 'no-reply', '@2x', '.png', '.jpg', '.gif',
    '.svg', '.woff', '.ttf', 'schema.org', 'w3.org', 'jquery', 'wpcf7',
    'facebook.com', 'google.com', 'apple.com', 'twitter.com', 'youtube.com',
    'paypal', 'bugsnag', 'rollbar', 'logrocket', 'cloudflare', 'wordpress.org',
}

# Prefixos de email genérico — válidos mas de baixa confiança comercial
_EMAIL_GENERIC_PREFIXES = {
    'info', 'geral', 'contact', 'contacto', 'hello', 'support', 'suporte',
    'admin', 'office', 'mail', 'email', 'vendas', 'atendimento', 'comercial',
}


def _extract_email_quality(email: str) -> str:
    """
    Devolve 'alta', 'media' ou 'baixa' confiança para o email.
    - alta:  email com nome próprio / nome de empresa antes do @
    - media: email com prefixo genérico mas domínio próprio
    - baixa: email junk ou de plataforma genérica
    """
    if not email:
        return "desconhecida"
    local = email.split("@")[0].lower() if "@" in email else ""
    if any(j in email.lower() for j in _EMAIL_JUNK):
        return "baixa"
    if local in _EMAIL_GENERIC_PREFIXES:
        return "media"
    return "alta"


def _extract_contacts_from_html(html: str) -> tuple:
    """
    Extract a business email and a Portuguese phone number from HTML.
    Returns (email_or_None, telefone_or_None).
    """
    email    = None
    telefone = None

    # Email
    candidates = re.findall(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}', html
    )
    for c in candidates:
        c_low = c.lower()
        if not any(j in c_low for j in _EMAIL_JUNK):
            email = c
            break

    # Telefone português (9 dígitos começando por 2, 3, 6, 7 ou 9)
    html_text = re.sub(r'<[^>]+>', ' ', html)
    phone_matches = re.findall(
        r'(?:(?:\+351|00351)[\s\-.]?)?([23679]\d{2}[\s\-.]?\d{3}[\s\-.]?\d{3})',
        html_text
    )
    for raw in phone_matches:
        cleaned = re.sub(r'[\s\-.]', '', raw)
        if re.match(r'^[23679]\d{8}$', cleaned):
            telefone = cleaned
            break

    return email, telefone


def _extract_instagram_url(html: str) -> Optional[str]:
    """
    CORRIGIDO: Extrai URL real de Instagram — exige handle com ≥3 chars.
    Não aceita apenas menções genéricas a instagram.com.
    Ignora links de posts, reels, stories, explore, sharer.
    """
    _INVALID_PATHS = ['/p/', '/reel/', '/stories/', '/explore/', 'sharer',
                      '/tv/', '/ar/', '/developer', '/help']
    # Padrão: https://www.instagram.com/HANDLE/ onde HANDLE tem ≥3 chars e não é path de post
    for m in re.finditer(
        r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]{3,30})/?(?:[\s"\'<>]|$)',
        html
    ):
        full_url = m.group(0).rstrip(' "\'<>')
        handle   = m.group(1)
        if any(inv in full_url for inv in _INVALID_PATHS):
            continue
        # Handle não pode ser só números (links de story/highlight)
        if re.match(r'^\d+$', handle):
            continue
        return f"https://www.instagram.com/{handle}"
    return None


def _extract_facebook_url(html: str) -> Optional[str]:
    """
    CORRIGIDO: Extrai URL real de página de Facebook.
    Ignora links de partilha, trackers e plugins.
    """
    _INVALID_PATHS = ['sharer', '/tr?', 'plugins', 'dialog', '/share',
                      'facebook.com/login', 'facebook.com/help']
    for m in re.finditer(
        r'https?://(?:www\.)?facebook\.com/([A-Za-z0-9_.]{3,80})/?(?:[\s"\'<>]|$)',
        html
    ):
        full_url = m.group(0).rstrip(' "\'<>')
        if any(inv in full_url for inv in _INVALID_PATHS):
            continue
        return full_url.rstrip('/')
    return None


def check_digital_presence(website: Optional[str]) -> dict:
    """
    Check digital presence for a company.
    Returns boolean flags, social media URLs, and contact info.

    CORRIGIDO:
    - tem_instagram / tem_facebook exigem URL real extraída (não só menção)
    - email de contacto classifica confiança
    """
    _empty = {
        "tem_website": False, "tem_loja_online": False,
        "tem_gtm": False, "tem_ga4": False,
        "tem_pixel_meta": False, "tem_google_ads": False,
        "tem_facebook_ads": False,
        "tem_instagram": False, "tem_facebook": False, "tem_linkedin": False,
        "instagram": None, "facebook": None, "linkedin": None,
        "email": None, "telefone": None,
        "confianca_email": "desconhecida", "confianca_telefone": "desconhecida",
    }
    if not website:
        return _empty

    url  = website if website.startswith("http") else f"https://{website}"
    html = fetch_url(url, timeout=10)
    if not html:
        return {**_empty, "tem_website": True}

    html_lower = html.lower()

    # Redes sociais — URLs reais
    instagram_url = _extract_instagram_url(html)
    facebook_url  = _extract_facebook_url(html)

    linkedin_url = None
    li_match = re.search(
        r'https?://(?:www\.)?linkedin\.com/(?:company|in)/([A-Za-z0-9_\-]{3,80})/?',
        html
    )
    if li_match:
        linkedin_url = li_match.group(0).rstrip('/')

    # Contactos na homepage
    email_found, telefone_found = _extract_contacts_from_html(html)

    # Se não encontrou na homepage, tenta páginas de contacto
    if not email_found or not telefone_found:
        base = url.rstrip('/')
        for path in ('/contacto', '/contactos', '/contact', '/contacte-nos', '/sobre', '/about'):
            try:
                contact_html = fetch_url(f"{base}{path}", timeout=4)
                if contact_html:
                    e, t = _extract_contacts_from_html(contact_html)
                    if not email_found and e:
                        email_found = e
                    if not telefone_found and t:
                        telefone_found = t
                if email_found and telefone_found:
                    break
            except Exception:
                pass

    confianca_email    = _extract_email_quality(email_found) if email_found else "desconhecida"
    confianca_telefone = "media" if telefone_found else "desconhecida"

    return {
        "tem_website":      True,
        "tem_loja_online":  any(kw in html_lower for kw in
                                ["woocommerce", "shopify", "cart", "carrinho", "checkout", "loja"]),
        "tem_gtm":          "googletagmanager.com" in html_lower or "gtm.js" in html_lower,
        "tem_ga4":          "gtag" in html_lower or "google-analytics" in html_lower or "ga4" in html_lower,
        "tem_pixel_meta":   "connect.facebook.net" in html_lower or "fbq(" in html_lower,
        "tem_google_ads":   "googleadservices" in html_lower or "conversion" in html_lower,
        "tem_facebook_ads": "connect.facebook.net" in html_lower,
        # CORRIGIDO: apenas True se URL real encontrada
        "tem_instagram":    instagram_url is not None,
        "tem_facebook":     facebook_url is not None,
        "tem_linkedin":     linkedin_url is not None,
        "instagram":        instagram_url,
        "facebook":         facebook_url,
        "linkedin":         linkedin_url,
        "email":            email_found,
        "telefone":         telefone_found,
        "confianca_email":  confianca_email,
        "confianca_telefone": confianca_telefone,
    }


def scrape_all_sources(nicho: str, localidade: str, max_results: int = 20) -> list:
    """
    Agrega empresas de TODAS as fontes disponíveis e deduplica.

    CORRIGIDO:
    - Deduplicação multi-campo: nome normalizado + telefone + domínio do site
    - Merge de campos em falta de fontes secundárias
    """
    try:
        from lib.source_wikidata import scrape_wikidata
    except Exception:
        scrape_wikidata = lambda *a, **kw: []  # noqa

    try:
        from lib.source_infopaginas import scrape_infopaginas, scrape_guiaempresa
    except Exception:
        scrape_infopaginas = lambda *a, **kw: []  # noqa
        scrape_guiaempresa = lambda *a, **kw: []  # noqa

    try:
        from lib.source_apis import scrape_foursquare, scrape_here, scrape_google_places
    except Exception:
        scrape_foursquare   = lambda *a, **kw: []  # noqa
        scrape_here         = lambda *a, **kw: []  # noqa
        scrape_google_places = lambda *a, **kw: []  # noqa

    per_source = max(max_results, 20)
    all_raw: list = []

    sources = [
        ("OSM Overpass",   lambda: scrape_paginas_amarelas(nicho, localidade, per_source)),
        ("Wikidata",       lambda: scrape_wikidata(nicho, localidade, per_source)),
        ("Foursquare",     lambda: scrape_foursquare(nicho, localidade, per_source)),
        ("HERE",           lambda: scrape_here(nicho, localidade, per_source)),
        ("Google Places",  lambda: scrape_google_places(nicho, localidade, per_source)),
        ("infopaginas",    lambda: scrape_infopaginas(nicho, localidade, per_source)),
        ("guiaempresa",    lambda: scrape_guiaempresa(nicho, localidade, per_source)),
    ]

    for name, fn in sources:
        try:
            results = fn()
            print(f"[SCRAPER] {name}: {len(results)} results", flush=True)
            for r in results:
                r.setdefault("fonte_raw", name)
            all_raw.extend(results)
        except Exception as e:
            print(f"[SCRAPER] {name}: ERROR - {type(e).__name__}: {e}", flush=True)

    # ── Deduplicação multi-campo ──────────────────────────────────────────────
    # Índices: nome_normalizado, telefone, domínio_site
    seen_name:   dict = {}   # nome_normalizado → idx na lista `merged`
    seen_phone:  dict = {}   # telefone → idx
    seen_domain: dict = {}   # domínio → idx
    merged: list = []

    for company in all_raw:
        name = company.get("nome", "").strip()
        if not name or len(name) < 2:
            continue

        norm_name = _normalize_name_for_dedup(name)
        phone     = _normalize_phone(company.get("telefone", ""))
        domain    = _extract_domain(company.get("website", ""))

        # Verificar se já existe por qualquer um dos campos de dedup
        existing_idx = None
        if norm_name and norm_name in seen_name:
            existing_idx = seen_name[norm_name]
        elif phone and phone in seen_phone:
            existing_idx = seen_phone[phone]
        elif domain and domain in seen_domain:
            existing_idx = seen_domain[domain]

        if existing_idx is not None:
            # Merge: preencher campos em falta no registo existente
            primary = merged[existing_idx]
            for field in ("telefone", "email", "website", "morada",
                          "codigo_postal", "instagram", "facebook", "linkedin"):
                if not primary.get(field) and company.get(field):
                    primary[field] = company[field]
            # Adicionar fonte ao array de fontes
            fontes_existentes = primary.get("_fontes", [primary.get("fonte_raw", "")])
            nova_fonte = company.get("fonte_raw", "")
            if nova_fonte and nova_fonte not in fontes_existentes:
                fontes_existentes.append(nova_fonte)
            primary["_fontes"] = fontes_existentes
        else:
            # Novo registo
            idx = len(merged)
            company["_fontes"] = [company.get("fonte_raw", "")]
            merged.append(company)
            if norm_name:
                seen_name[norm_name] = idx
            if phone:
                seen_phone[phone] = idx
            if domain:
                seen_domain[domain] = idx

    return merged[:max_results]


# ── SCORE 0-100 E CLASSIFICAÇÃO ───────────────────────────────────────────────

def calculate_scores(data: dict) -> dict:
    """
    REESCRITO: Score de qualidade do lead em escala 0-100.

    Pontuações positivas:
      +20  site oficial encontrado e acessível
      +20  telefone comercial
      +25  email (com bónus/penalização por confiança)
      +10  Instagram oficial (URL real)
      +8   Facebook oficial (URL real)
      +7   LinkedIn oficial
      +5   morada completa
      +3   código postal
      +10  múltiplas fontes coerentes (≥2 fontes diferentes)

    Penalizações:
      -10  sem telefone
      -15  sem email
      -20  sem site E sem rede social real
      -15  inconsistência (tem_website=True mas sem email e sem telefone)
      -8   email genérico (info@, geral@, contact@...)
      -5   Instagram detectado só como booleano (sem URL real)

    Legado (score_maturidade_digital 0-10 e score_oportunidade_comercial 0-10):
      mantidos para compatibilidade com o dashboard existente.
    """
    score = 0

    # ── Pontuações positivas ─────────────────────────────────────────────────
    if data.get("tem_website"):
        score += 20

    if data.get("telefone"):
        score += 20
        # Bónus: confiança alta no telefone
        if data.get("confianca_telefone") == "alta":
            score += 3

    if data.get("email"):
        confianca = data.get("confianca_email", "desconhecida")
        if confianca == "alta":
            score += 25
        elif confianca == "media":
            score += 17
        else:
            score += 8

    # Redes sociais — apenas URLs reais valem pontuação completa
    if data.get("instagram"):       # URL real
        score += 10
    if data.get("facebook"):        # URL real
        score += 8
    if data.get("linkedin"):        # URL real
        score += 7

    if data.get("morada"):
        score += 5
    if data.get("codigo_postal"):
        score += 3

    # Múltiplas fontes
    fontes = data.get("_fontes") or []
    if isinstance(fontes, list) and len(fontes) >= 2:
        score += 10
    elif isinstance(fontes, str):
        # Compatibilidade: se for string com vírgulas
        if len(fontes.split(",")) >= 2:
            score += 10

    # ── Penalizações ─────────────────────────────────────────────────────────
    if not data.get("telefone"):
        score -= 10

    if not data.get("email"):
        score -= 15

    if not data.get("tem_website") and not data.get("instagram") and not data.get("facebook"):
        score -= 20

    # Site existe mas sem nenhum contacto no site (sinal de site abandonado/inútil)
    if data.get("tem_website") and not data.get("email") and not data.get("telefone"):
        score -= 8

    # Email genérico
    if data.get("email") and data.get("confianca_email") == "media":
        score -= 8

    # Garantir que fica entre 0 e 100
    score_qualidade = max(0, min(100, score))

    # ── Maturidade digital (escala 0-10, mantida para compatibilidade) ────────
    md = 0
    if data.get("tem_website"):    md += 3
    if data.get("tem_instagram") or data.get("tem_facebook"): md += 2
    if data.get("tem_ga4") or data.get("tem_gtm"):            md += 2
    if data.get("tem_pixel_meta") or data.get("tem_google_ads"): md += 2
    if data.get("tem_loja_online"): md += 1
    score_maturidade = min(10.0, float(md))

    # ── Oportunidade comercial (0-10, invertido: menos digital = mais oportunidade) ─
    oportunidade = 10.0 - score_maturidade
    if not data.get("tem_pixel_meta") and not data.get("tem_google_ads"):
        oportunidade = min(10.0, oportunidade + 2)
    score_oportunidade = round(oportunidade, 1)

    # ── Prioridade SDR (0-10) ─────────────────────────────────────────────────
    contact_score = 0
    if data.get("telefone"): contact_score += 3
    if data.get("email"):    contact_score += 2
    prioridade     = (score_oportunidade * 0.6 + contact_score) * (10 / 8)
    score_prioridade = min(10.0, round(prioridade, 1))

    return {
        "score_qualidade_lead":           score_qualidade,
        "score_maturidade_digital":       round(score_maturidade, 1),
        "score_oportunidade_comercial":   score_oportunidade,
        "score_prioridade_sdr":           score_prioridade,
    }


def classify_lead(data: dict) -> tuple:
    """
    Classifica o lead com base no score_qualidade_lead.

    Retorna (classificacao, motivo_descarte_ou_None)

    EXCELENTE: score ≥ 60
    BOM:       score ≥ 35
    FRACO:     score ≥ 10
    LIXO:      score < 10  OU sem qualquer contacto real
    """
    score = data.get("score_qualidade_lead", 0)

    # Regra absoluta de LIXO: sem nenhum meio de contacto real
    sem_contacto = (
        not data.get("telefone") and
        not data.get("email") and
        not data.get("website") and
        not data.get("instagram") and
        not data.get("facebook")
    )
    if sem_contacto:
        return ("lixo", "Sem nenhum contacto real encontrado (sem telefone, email, site ou rede social)")

    if score < 10:
        return ("lixo", f"Score de qualidade demasiado baixo ({score}/100)")

    if score < 35:
        return ("fraco", None)

    if score < 60:
        return ("bom", None)

    return ("excelente", None)
