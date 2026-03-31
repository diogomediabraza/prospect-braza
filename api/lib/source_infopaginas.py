"""
Infopáginas.pt + Guia Empresa .pt — scraping gratuito de diretórios portugueses.
Não requer API key. Tenta acesso directo; se bloqueado, retorna lista vazia.
"""
import re
import urllib.request
import urllib.parse
from typing import Optional


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def _fetch_html(url: str, timeout: int = 12) -> str:
    import gzip
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            enc = r.headers.get("Content-Encoding", "")
            if "gzip" in enc:
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _clean_text(s: str) -> str:
    return re.sub(r'\s+', ' ', s.strip())


# ─── INFOPÁGINAS.PT ───────────────────────────────────────────────────────────

def scrape_infopaginas(nicho: str, localidade: str, max_results: int = 20) -> list:
    """
    Scraping de www.infopaginas.pt
    URL: /pesquisa/?q={nicho}&where={localidade}
    """
    q = urllib.parse.quote(nicho)
    w = urllib.parse.quote(localidade)
    url = f"https://www.infopaginas.pt/pesquisa/?q={q}&where={w}"

    html = _fetch_html(url)
    if not html or len(html) < 500:
        return []

    companies = []
    seen: set = set()

    # Padrões de extracção de cards de empresa
    # O site usa estruturas como <article class="listing-item ..."> ou <div class="result-...">
    # Tentamos múltiplos padrões para robustez
    card_patterns = [
        r'<article[^>]*class="[^"]*listing[^"]*"[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*result-item[^"]*"[^>]*>(.*?)</div>\s*</div>',
        r'<div[^>]*class="[^"]*empresa[^"]*"[^>]*>(.*?)</div>',
        r'<li[^>]*class="[^"]*listing[^"]*"[^>]*>(.*?)</li>',
    ]

    cards = []
    for pat in card_patterns:
        cards = re.findall(pat, html, re.DOTALL | re.IGNORECASE)
        if cards:
            break

    # Se não encontrou cards estruturados, tenta extracção por padrões de dados
    if not cards:
        return _extract_by_patterns(html, nicho, localidade, max_results)

    for card in cards:
        # Nome da empresa
        name_match = re.search(
            r'<h[123][^>]*>(.*?)</h[123]>|<a[^>]*class="[^"]*name[^"]*"[^>]*>(.*?)</a>|'
            r'class="[^"]*title[^"]*"[^>]*>(.*?)<',
            card, re.IGNORECASE | re.DOTALL
        )
        if not name_match:
            continue
        raw_name = next((g for g in name_match.groups() if g), "")
        name = _clean_text(re.sub(r'<[^>]+>', '', raw_name))
        if not name or len(name) < 2:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        company: dict = {"nome": name, "nicho": nicho, "localidade": localidade, "fonte_raw": "Infopáginas"}

        # Telefone
        phone_match = re.search(
            r'tel[^>]*href="tel:([^"]+)"|'
            r'class="[^"]*phone[^"]*"[^>]*>[^<]*?([\d\s\+\-\.]{9,})',
            card, re.IGNORECASE
        )
        if phone_match:
            phone = next((g for g in phone_match.groups() if g), "").replace(" ", "")
            if phone:
                company["telefone"] = phone

        # Website
        web_match = re.search(
            r'href="(https?://(?!infopaginas)[^"]+)"',
            card, re.IGNORECASE
        )
        if web_match:
            company["website"] = web_match.group(1)

        # Morada
        addr_match = re.search(
            r'class="[^"]*address[^"]*"[^>]*>(.*?)<(?:/|span|div)',
            card, re.IGNORECASE | re.DOTALL
        )
        if addr_match:
            morada = _clean_text(re.sub(r'<[^>]+>', '', addr_match.group(1)))
            if morada:
                company["morada"] = morada

        companies.append(company)
        if len(companies) >= max_results:
            break

    return companies


def _extract_by_patterns(html: str, nicho: str, localidade: str, max_results: int) -> list:
    """Extracção fallback por padrões globais de telefone/nome."""
    companies = []
    seen: set = set()

    # Tenta encontrar pares nome+telefone próximos no HTML
    # Padrão: texto entre tags seguido de número de telefone português
    segments = re.split(r'<hr|<div class="sep|<li class="result', html, flags=re.IGNORECASE)

    for seg in segments[1:]:
        name_match = re.search(r'<h[23][^>]*>([^<]{3,80})</h[23]>', seg)
        if not name_match:
            continue
        name = _clean_text(name_match.group(1))
        if not name or len(name) < 2:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        company: dict = {"nome": name, "nicho": nicho, "localidade": localidade, "fonte_raw": "Infopáginas"}

        phone_m = re.search(r'(\+?351[\s\-]?)?([239]\d{8})', seg)
        if phone_m:
            company["telefone"] = phone_m.group(2)

        web_m = re.search(r'href="(https?://(?!infopaginas)[^\s"]{10,})"', seg)
        if web_m:
            company["website"] = web_m.group(1)

        companies.append(company)
        if len(companies) >= max_results:
            break

    return companies


# ─── GUIA EMPRESA .PT ─────────────────────────────────────────────────────────

# Mapa de nichos para categorias do GuiaEmpresa
_GE_CATEGORIAS: dict[str, str] = {
    "restaurante":   "restaurantes",
    "restaurantes":  "restaurantes",
    "cafe":          "cafes-e-pastelarias",
    "cafes":         "cafes-e-pastelarias",
    "bar":           "bares",
    "clinica":       "clinicas",
    "clinicas":      "clinicas",
    "dentista":      "clinicas-dentarias",
    "dentistas":     "clinicas-dentarias",
    "farmacia":      "farmacias",
    "farmacias":     "farmacias",
    "hotel":         "hoteis",
    "hoteis":        "hoteis",
    "ginasio":       "ginasios",
    "ginasios":      "ginasios",
    "padaria":       "padarias",
    "padarias":      "padarias",
    "supermercado":  "supermercados",
    "supermercados": "supermercados",
    "cabeleireiro":  "cabeleireiros",
    "cabeleireiros": "cabeleireiros",
    "advogado":      "escritorios-de-advogados",
    "advogados":     "escritorios-de-advogados",
    "escola":        "escolas",
    "escolas":       "escolas",
    "veterinario":   "veterinarios",
    "veterinarios":  "veterinarios",
}


def scrape_guiaempresa(nicho: str, localidade: str, max_results: int = 20) -> list:
    """
    Scraping de www.guiaempresa.pt
    URL: /empresas/{categoria}/{localidade-slug}/
    """
    nicho_lower = nicho.lower().strip()
    categoria = _GE_CATEGORIAS.get(nicho_lower)
    if not categoria and nicho_lower.endswith("s"):
        categoria = _GE_CATEGORIAS.get(nicho_lower[:-1])
    if not categoria:
        categoria = urllib.parse.quote(nicho_lower)

    city_slug = localidade.lower().strip().replace(" ", "-")
    url = f"https://www.guiaempresa.pt/empresas/{categoria}/{city_slug}/"

    html = _fetch_html(url)
    if not html or len(html) < 500:
        # Fallback: try search URL
        q = urllib.parse.quote(f"{nicho} {localidade}")
        url = f"https://www.guiaempresa.pt/pesquisa/?q={q}"
        html = _fetch_html(url)
    if not html or len(html) < 500:
        return []

    companies = []
    seen: set = set()

    # GuiaEmpresa usa cartões de empresa com padrões específicos
    card_patterns = [
        r'<div[^>]*class="[^"]*empresa-card[^"]*"[^>]*>(.*?)</div>\s*</div>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*company[^"]*"[^>]*>(.*?)</div>',
        r'<li[^>]*class="[^"]*item[^"]*"[^>]*>(.*?)</li>',
    ]

    cards = []
    for pat in card_patterns:
        cards = re.findall(pat, html, re.DOTALL | re.IGNORECASE)
        if len(cards) > 2:
            break

    for card in cards:
        name_m = re.search(
            r'<h[123][^>]*>([^<]{2,100})</h[123]>|'
            r'class="[^"]*name[^"]*"[^>]*>([^<]{2,100})<',
            card, re.IGNORECASE
        )
        if not name_m:
            continue
        name = _clean_text(next((g for g in name_m.groups() if g), ""))
        if not name or len(name) < 2:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        company: dict = {"nome": name, "nicho": nicho, "localidade": localidade, "fonte_raw": "GuiaEmpresa"}

        phone_m = re.search(r'(\+?351[\s\-]?)?([239]\d{8})', card)
        if phone_m:
            company["telefone"] = phone_m.group(2)

        web_m = re.search(r'href="(https?://(?!guiaempresa)[^\s"]{10,})"', card, re.IGNORECASE)
        if web_m:
            company["website"] = web_m.group(1)

        addr_m = re.search(
            r'class="[^"]*morada[^"]*|address[^"]*"[^>]*>([^<]{5,100})<',
            card, re.IGNORECASE
        )
        if addr_m:
            company["morada"] = _clean_text(addr_m.group(1))

        companies.append(company)
        if len(companies) >= max_results:
            break

    return companies
