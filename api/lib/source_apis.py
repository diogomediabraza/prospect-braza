"""
Fontes com API key opcional — tier gratuito em todas:

  FOURSQUARE_API_KEY  → Foursquare Places  (950 calls/day grátis)
  HERE_API_KEY        → HERE Places        (250 000 calls/mês grátis)
  GOOGLE_PLACES_KEY   → Google Places      ($200 crédito/mês = ~7 000 detalhes grátis)

Se a variável de ambiente não estiver definida, a fonte é ignorada silenciosamente.
"""
import os
import json
import re
import urllib.request
import urllib.parse
from typing import Optional


def _get(url: str, headers: Optional[dict] = None, timeout: int = 15) -> Optional[dict]:
    """GET JSON de uma API REST."""
    req = urllib.request.Request(url, headers=headers or {
        "User-Agent": "ProspectBraza/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _normalize_phone(raw: str) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r'[\s\-\.\(\)+]', '', raw).lstrip("351")
    if re.match(r'^[23679]\d{8}$', cleaned):
        return cleaned
    return raw


# ─── FOURSQUARE PLACES (Free tier: 950 calls/day) ────────────────────────────
# Registo gratuito: https://foursquare.com/developers/

def scrape_foursquare(nicho: str, localidade: str, max_results: int = 20) -> list:
    """
    Foursquare Places Search v3.
    Requer env var FOURSQUARE_API_KEY (gratuito em https://foursquare.com/developers/).
    Devolve nome, morada, telefone, website, categorias.
    """
    api_key = os.environ.get("FOURSQUARE_API_KEY", "")
    if not api_key:
        return []

    params = urllib.parse.urlencode({
        "query":  nicho,
        "near":   f"{localidade}, Portugal",
        "limit":  min(max_results * 2, 50),
        "fields": "name,location,tel,website,email,social_media,categories",
    })
    url = f"https://api.foursquare.com/v3/places/search?{params}"

    data = _get(url, headers={
        "Authorization": api_key,
        "Accept": "application/json",
    })
    if not data:
        return []

    companies = []
    seen: set = set()

    for r in data.get("results", []):
        name = r.get("name", "").strip()
        if not name or len(name) < 2:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        loc = r.get("location", {})
        company: dict = {
            "nome":       name,
            "nicho":      nicho,
            "localidade": localidade,
            "fonte_raw":  "Foursquare",
        }

        # Morada
        parts = []
        if loc.get("address"):
            parts.append(loc["address"])
        if loc.get("locality") and loc["locality"].lower() != localidade.lower():
            parts.append(loc["locality"])
        if parts:
            company["morada"] = ", ".join(parts)

        if loc.get("postcode"):
            company["codigo_postal"] = loc["postcode"]

        phone = _normalize_phone(r.get("tel", ""))
        if phone:
            company["telefone"] = phone

        if r.get("website"):
            w = r["website"]
            company["website"] = w if w.startswith("http") else f"https://{w}"

        if r.get("email"):
            company["email"] = r["email"]

        social = r.get("social_media", {})
        if social.get("instagram"):
            ig = social["instagram"]
            company["instagram"] = ig if ig.startswith("http") else f"https://www.instagram.com/{ig.lstrip('@')}"
        if social.get("facebook"):
            fb = social["facebook"]
            company["facebook"] = fb if fb.startswith("http") else f"https://www.facebook.com/{fb.lstrip('@')}"

        companies.append(company)
        if len(companies) >= max_results:
            break

    return companies


# ─── HERE PLACES (Free tier: 250 000 calls/mês) ──────────────────────────────
# Registo gratuito: https://developer.here.com/

def scrape_here(nicho: str, localidade: str, max_results: int = 20) -> list:
    """
    HERE Geocoding & Search API v1.
    Requer env var HERE_API_KEY (gratuito em https://developer.here.com/).
    Devolve nome, morada, código postal, telefone, website, categorias.
    """
    api_key = os.environ.get("HERE_API_KEY", "")
    if not api_key:
        return []

    # Primeiro geocodifica a cidade para obter coordenadas
    geo_params = urllib.parse.urlencode({
        "q": f"{localidade}, Portugal",
        "limit": 1,
        "apikey": api_key,
    })
    geo = _get(f"https://geocode.search.hereapi.com/v1/geocode?{geo_params}")
    if not geo or not geo.get("items"):
        return []

    pos = geo["items"][0].get("position", {})
    lat, lng = pos.get("lat"), pos.get("lng")
    if not lat or not lng:
        return []

    # Pesquisa de lugares
    params = urllib.parse.urlencode({
        "q":      nicho,
        "at":     f"{lat},{lng}",
        "in":     "countryCode:PRT",
        "limit":  min(max_results * 2, 100),
        "lang":   "pt",
        "apikey": api_key,
    })
    data = _get(f"https://discover.search.hereapi.com/v1/discover?{params}")
    if not data:
        return []

    companies = []
    seen: set = set()

    for item in data.get("items", []):
        name = item.get("title", "").strip()
        if not name or len(name) < 2:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        addr = item.get("address", {})
        company: dict = {
            "nome":       name,
            "nicho":      nicho,
            "localidade": localidade,
            "fonte_raw":  "HERE Places",
        }

        morada_parts = []
        if addr.get("street"):
            house = addr.get("houseNumber", "")
            morada_parts.append(f"{addr['street']} {house}".strip())
        if addr.get("city") and addr["city"].lower() != localidade.lower():
            morada_parts.append(addr["city"])
        if morada_parts:
            company["morada"] = ", ".join(morada_parts)

        if addr.get("postalCode"):
            company["codigo_postal"] = addr["postalCode"]

        contacts = item.get("contacts", [{}])[0] if item.get("contacts") else {}
        phones = contacts.get("phone", [])
        if phones:
            company["telefone"] = _normalize_phone(phones[0].get("value", ""))

        websites = contacts.get("www", [])
        if websites:
            w = websites[0].get("value", "")
            if w:
                company["website"] = w if w.startswith("http") else f"https://{w}"

        companies.append(company)
        if len(companies) >= max_results:
            break

    return companies


# ─── GOOGLE PLACES (Free: $200 crédito/mês ≈ 7 000 detalhes grátis) ──────────
# Registo: https://console.cloud.google.com/ → activa "Places API"

def scrape_google_places(nicho: str, localidade: str, max_results: int = 20) -> list:
    """
    Google Places Text Search + Place Details.
    Requer env var GOOGLE_PLACES_KEY.
    $200 de crédito grátis/mês = ~28 000 Text Searches ou ~7 000 Place Details grátis.
    A fonte mais rica: telefone, website, morada, código postal, horas, avaliações.
    """
    api_key = os.environ.get("GOOGLE_PLACES_KEY", "")
    if not api_key:
        return []

    # Text Search (mais barata: $32/1000)
    params = urllib.parse.urlencode({
        "query":  f"{nicho} em {localidade} Portugal",
        "region": "pt",
        "language": "pt",
        "key":    api_key,
    })
    data = _get(f"https://maps.googleapis.com/maps/api/place/textsearch/json?{params}")
    if not data or data.get("status") not in ("OK", "ZERO_RESULTS"):
        return []

    companies = []
    seen: set = set()
    results = data.get("results", [])[:max_results * 2]

    for r in results:
        name = r.get("name", "").strip()
        if not name or len(name) < 2:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        company: dict = {
            "nome":       name,
            "nicho":      nicho,
            "localidade": localidade,
            "fonte_raw":  "Google Places",
        }

        addr = r.get("formatted_address", "")
        if addr:
            # Remove "Portugal" do final para limpar
            addr_clean = re.sub(r',?\s*Portugal\s*$', '', addr).strip()
            company["morada"] = addr_clean

        # Place Details para obter telefone + website (mais cara: $170/1000)
        # Só chama se tivermos place_id
        place_id = r.get("place_id")
        if place_id:
            detail_params = urllib.parse.urlencode({
                "place_id": place_id,
                "fields":   "formatted_phone_number,website,url",
                "language": "pt",
                "key":      api_key,
            })
            detail = _get(
                f"https://maps.googleapis.com/maps/api/place/details/json?{detail_params}"
            )
            if detail and detail.get("result"):
                res = detail["result"]
                phone = _normalize_phone(res.get("formatted_phone_number", ""))
                if phone:
                    company["telefone"] = phone
                if res.get("website"):
                    company["website"] = res["website"]

        companies.append(company)
        if len(companies) >= max_results:
            break

    return companies
