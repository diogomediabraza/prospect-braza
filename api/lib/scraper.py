"""
Scraper for Páginas Amarelas (Portugal) — adapted for serverless.
Runs synchronously within a Vercel serverless function with a timeout.
"""
import re
import time
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from typing import Optional


class CompanyParser(HTMLParser):
    """Simple HTML parser to extract company listings."""

    def __init__(self):
        super().__init__()
        self.companies = []
        self._current = {}
        self._in_listing = False
        self._capture = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        # Company listing container
        if tag == "article" and "listing" in cls:
            self._in_listing = True
            self._current = {}

        if self._in_listing:
            # Company name
            if tag in ("h2", "h3") and "company-name" in cls:
                self._capture = "nome"
            # Phone
            elif tag == "span" and "phone" in cls:
                self._capture = "telefone"
            # Address
            elif tag in ("span", "div") and "address" in cls:
                self._capture = "morada"
            # Website link
            elif tag == "a" and "website" in cls:
                href = attrs_dict.get("href", "")
                if href and "paginasamarelas" not in href:
                    self._current["website"] = href
            # Category/nicho
            elif tag == "span" and "category" in cls:
                self._capture = "nicho"

    def handle_endtag(self, tag):
        if tag == "article" and self._in_listing:
            if self._current.get("nome"):
                self.companies.append(dict(self._current))
            self._in_listing = False
            self._current = {}
        self._capture = None

    def handle_data(self, data):
        if self._capture and self._in_listing:
            text = data.strip()
            if text:
                self._current[self._capture] = text
            self._capture = None


def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch a URL with a user-agent header."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ProspectBraza/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-PT,pt;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def scrape_paginas_amarelas(
    nicho: str,
    localidade: str,
    max_results: int = 50,
) -> list[dict]:
    """
    Scrape Páginas Amarelas for companies.
    Returns list of raw company dicts.
    """
    results = []
    page = 1
    max_pages = max(1, max_results // 20)

    nicho_enc = urllib.parse.quote(nicho)
    local_enc = urllib.parse.quote(localidade)

    while len(results) < max_results and page <= max_pages:
        url = f"https://www.paginasamarelas.pt/resultados/{nicho_enc}/{local_enc}?page={page}"
        html = fetch_url(url)

        if not html:
            break

        parser = CompanyParser()
        parser.feed(html)

        if not parser.companies:
            # Fallback: extract basic data from raw HTML
            raw = extract_basic_from_html(html, nicho, localidade)
            results.extend(raw)
            break

        results.extend(parser.companies)
        page += 1
        time.sleep(0.5)  # polite delay

    return results[:max_results]


def extract_basic_from_html(html: str, nicho: str, localidade: str) -> list[dict]:
    """Fallback: extract company names and phones via regex."""
    results = []

    # Look for structured data (JSON-LD)
    json_ld_pattern = re.compile(
        r'"name"\s*:\s*"([^"]{3,80})".*?"telephone"\s*:\s*"([^"]+)"',
        re.DOTALL,
    )
    for match in json_ld_pattern.finditer(html):
        results.append({
            "nome": match.group(1).strip(),
            "telefone": match.group(2).strip(),
            "nicho": nicho,
            "localidade": localidade,
        })

    # Look for phone patterns + nearby text
    if not results:
        phone_pattern = re.compile(r"\b(2\d{8}|9\d{8})\b")
        phones = phone_pattern.findall(html)
        for phone in phones[:20]:
            results.append({
                "nome": f"Empresa em {localidade}",
                "telefone": phone,
                "nicho": nicho,
                "localidade": localidade,
            })

    return results


def check_digital_presence(website: Optional[str]) -> dict:
    """
    Check basic digital presence for a company.
    Returns dict with boolean flags.
    """
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
            "tem_website": True,  # URL exists but couldn't fetch
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


def calculate_scores(data: dict) -> dict:
    """Calculate scoring for a company based on digital presence."""
    # Maturidade Digital (0-10)
    md = 0
    if data.get("tem_website"):
        md += 3
    if data.get("tem_instagram") or data.get("tem_facebook"):
        md += 2
    if data.get("tem_ga4") or data.get("tem_gtm"):
        md += 2
    if data.get("tem_pixel_meta") or data.get("tem_google_ads"):
        md += 2
    if data.get("tem_loja_online"):
        md += 1
    score_maturidade = min(10.0, md)

    # Oportunidade Comercial (0-10) — inverse of maturity
    # Companies with low maturity = high opportunity
    oportunidade = 10 - score_maturidade
    # Bump if no ads at all
    if not data.get("tem_pixel_meta") and not data.get("tem_google_ads"):
        oportunidade = min(10.0, oportunidade + 2)
    score_oportunidade = round(oportunidade, 1)

    # Prioridade SDR (0-10) — balanced score
    # Has contact info = easier to reach
    contact_score = 0
    if data.get("telefone"):
        contact_score += 3
    if data.get("email"):
        contact_score += 2

    prioridade = (score_oportunidade * 0.6 + contact_score) * (10 / 8)
    score_prioridade = min(10.0, round(prioridade, 1))

    return {
        "score_maturidade_digital": round(score_maturidade, 1),
        "score_oportunidade_comercial": score_oportunidade,
        "score_prioridade_sdr": score_prioridade,
    }
