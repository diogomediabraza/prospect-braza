"""
Scraper for pai.pt (ex-Páginas Amarelas, Portugal) — adapted for serverless.
Runs synchronously within a Vercel serverless function with a timeout.
"""
import re
import time
import gzip as _gzip
import urllib.request
import urllib.parse
from typing import Optional


def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch a URL with browser-like headers, handling gzip."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            enc = response.headers.get("Content-Encoding", "")
            if "gzip" in enc:
                raw = _gzip.decompress(raw)
            return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_companies_pai(html: str, nicho: str, localidade: str) -> list[dict]:
    """Extract company listings from pai.pt HTML."""
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
        seen_ids: set = set()
        for m in link_pattern.finditer(html):
            pid = m.group(1)
            text = m.group(3).strip()
            if pid not in seen_ids and len(text) > 3:
                seen_ids.add(pid)
                names.append(text)
    if not names:
        seen_slugs: set = set()
        for slug in re.findall(r'href="/paginas/\d+-([^"]+)"', html):
            if slug not in seen_slugs:
                seen_slugs.add(slug)
                names.append(slug.replace("-", " ").title())
    results = []
    for i, name in enumerate(names):
        entry: dict = {"nome": name, "nicho": nicho, "localidade": localidade}
        if i < len(phones):
            entry["telefone"] = phones[i]
        results.append(entry)
    return results


def scrape_paginas_amarelas(
    nicho: str,
    localidade: str,
    max_results: int = 50,
) -> list[dict]:
    """Scrape pai.pt for companies."""
    results: list = []
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
        html = fetch_url(url)
        if not html:
            break
        companies = extract_companies_pai(html, nicho, localidade)
        if not companies:
            break
        results.extend(companies)
        page += 1
        time.sleep(0.5)
    seen: set = set()
    unique: list = []
    for c in results:
        if c["nome"] not in seen:
            seen.add(c["nome"])
            unique.append(c)
    return unique[:max_results]


def check_digital_presence(website) -> dict:
    """Check basic digital presence for a company."""
    if not website:
        return {"tem_website": False, "tem_loja_online": False, "tem_gtm": False,
                "tem_ga4": False, "tem_pixel_meta": False, "tem_google_ads": False,
                "tem_facebook_ads": False}
    url = website if website.startswith("http") else f"https://{website}"
    html = fetch_url(url, timeout=10)
    if not html:
        return {"tem_website": True, "tem_loja_online": False, "tem_gtm": False,
                "tem_ga4": False, "tem_pixel_meta": False, "tem_google_ads": False,
                "tem_facebook_ads": False}
    h = html.lower()
    return {
        "tem_website": True,
        "tem_loja_online": any(k in h for k in ["woocommerce","shopify","cart","carrinho","checkout","loja"]),
        "tem_gtm": "googletagmanager.com" in h or "gtm.js" in h,
        "tem_ga4": "gtag" in h or "google-analytics" in h or "ga4" in h,
        "tem_pixel_meta": "connect.facebook.net" in h or "fbq(" in h,
        "tem_google_ads": "googleadservices" in h or "conversion" in h,
        "tem_facebook_ads": "connect.facebook.net" in h,
    }


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
