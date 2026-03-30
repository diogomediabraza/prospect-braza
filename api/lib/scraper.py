"""
Scraper for pai.pt (ex-Páginas Amarelas, Portugal) — adapted for serverless.
Runs synchronously within a Vercel serverless function with a timeout.
"""
import re
import time
import gzip as _gzip
import zlib
import urllib.request
import urllib.parse
import http.cookiejar
from typing import Optional


def _make_opener():
    """Create an opener with cookie support and browser-like headers."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPSHandler(),
    )
    opener.addheaders = [
        ("User-Agent", (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )),
        ("Accept", (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        )),
        ("Accept-Language", "pt-PT,pt;q=0.9,en;q=0.8"),
        ("Accept-Encoding", "gzip, deflate"),
        ("Connection", "keep-alive"),
        ("Upgrade-Insecure-Requests", "1"),
        ("Cache-Control", "max-age=0"),
    ]
    return opener


def _decompress(raw, encoding):
    """Decompress response body."""
    if "gzip" in encoding:
        return _gzip.decompress(raw)
    if "deflate" in encoding:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def fetch_url(url, timeout=15, opener=None):
    """Fetch a URL using opener (with cookies), handling gzip/deflate."""
    if opener is None:
        opener = _make_opener()
    try:
        with opener.open(url, timeout=timeout) as response:
            raw = response.read()
            enc = response.headers.get("Content-Encoding", "")
            raw = _decompress(raw, enc)
            return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _warm_up_session(opener):
    """Visit homepage first to establish session cookies."""
    try:
        with opener.open("https://www.pai.pt/", timeout=10) as r:
            r.read()
    except Exception:
        pass


def extract_companies_pai(html, nicho, localidade):
    """
    Extract company listings from pai.pt HTML.

    pai.pt structure:
      - Company names are in <h2> or <h3> headings that contain
        an <a href="/paginas/{id}-{slug}"> link.
      - Phone numbers appear as <a href="tel:XXXXXXXXX"> links.
    """
    heading_pattern = re.compile(
        r'<h[23][^>]*>(?:[^<]|<(?!/h[23]))*?'
        r'href="/paginas/\d+[^"]*"[^>]*>\s*([^<]{3,100})\s*</a>',
        re.IGNORECASE | re.DOTALL,
    )
    link_pattern = re.compile(
        r'href="/paginas/(\d+)-([^"]+)"[^>]*>\s*([^<]{3,100})\s*</a>',
        re.IGNORECASE,
    )
    tel_pattern = re.compile(r'href="tel:(\+?351)?(\d{9})"')

    phones = [m.group(2) for m in tel_pattern.finditer(html)]
    names = [m.group(1).strip() for m in heading_pattern.finditer(html)]

    if not names:
        seen_ids = set()
        for m in link_pattern.finditer(html):
            pid = m.group(1)
            text = m.group(3).strip()
            if pid not in seen_ids and len(text) > 3:
                seen_ids.add(pid)
                names.append(text)

    if not names:
        seen_slugs = set()
        for slug in re.findall(r'href="/paginas/\d+-([^"]+)"', html):
            if slug not in seen_slugs:
                seen_slugs.add(slug)
                names.append(slug.replace("-", " ").title())

    results = []
    for i, name in enumerate(names):
        entry = {"nome": name, "nicho": nicho, "localidade": localidade}
        if i < len(phones):
            entry["telefone"] = phones[i]
        results.append(entry)
    return results


def scrape_paginas_amarelas(nicho, localidade, max_results=50):
    """Scrape pai.pt for companies. Returns list of raw company dicts."""
    opener = _make_opener()
    _warm_up_session(opener)

    results = []
    page = 1
    max_pages = max(1, (max_results + 9) // 10)
    nicho_enc = urllib.parse.quote(nicho)
    local_enc = urllib.parse.quote_plus(localidade)

    while len(results) < max_results and page <= max_pages:
        url = (
            "https://www.pai.pt/searches"
            "?search%5Bquery%5D=" + nicho_enc
            + "&search%5Blocation_value%5D=" + local_enc
            + "&search%5Blocation%5D=Portugal"
            "&commit=Procurar"
            "&page=" + str(page)
        )
        html = fetch_url(url, opener=opener)
        if not html:
            break
        companies = extract_companies_pai(html, nicho, localidade)
        if not companies:
            break
        results.extend(companies)
        page += 1
        time.sleep(0.5)

    seen = set()
    unique = []
    for c in results:
        if c["nome"] not in seen:
            seen.add(c["nome"])
            unique.append(c)
    return unique[:max_results]


def check_digital_presence(website):
    """Check basic digital presence for a company."""
    if not website:
        return {
            "tem_website": False,
            "tem_loja_online": False,
            "tem_gtm": False,
            "tem_ga4": False,
            "tem_pixel_meta": False,
            "tem_google_ads": False,
            "tem_facebook_ads": False,
        }
    url = website if website.startswith("http") else f"https://{website}"
    html = fetch_url(url, timeout=10)
    if not html:
        return {
            "tem_website": True,
            "tem_loja_online": False,
            "tem_gtm": False,
            "tem_ga4": False,
            "tem_pixel_meta": False,
            "tem_google_ads": False,
            "tem_facebook_ads": False,
        }
    html_lower = html.lower()
    return {
        "tem_website": True,
        "tem_loja_online": any(
            kw in html_lower
            for kw in ["woocommerce", "shopify", "cart", "carrinho", "checkout", "loja"]
        ),
        "tem_gtm": "googletagmanager.com" in html_lower or "gtm.js" in html_lower,
        "tem_ga4": "gtag" in html_lower or "google-analytics" in html_lower or "ga4" in html_lower,
        "tem_pixel_meta": "connect.facebook.net" in html_lower or "fbq(" in html_lower,
        "tem_google_ads": "googleadservices" in html_lower or "conversion" in html_lower,
        "tem_facebook_ads": "connect.facebook.net" in html_lower,
    }


def calculate_scores(data):
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
