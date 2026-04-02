"""
Níveis 1 e 2 — Enriquecimento via pesquisa web e redes sociais.

Nível 1: DuckDuckGo para encontrar website/telefone de empresas sem dados.
Nível 2: Pesquisa Instagram e Facebook pelo nome da empresa, raspa a bio
         para extrair email, telefone e website.

Design para Vercel Hobby (60s total):
  - Timeouts curtos (4-6s) para não bloquear o pipeline
  - Falha silenciosa — nunca lança exceção
  - Só activa se a empresa não tiver o campo em falta
"""
import re
import gzip as _gzip
import urllib.request
import urllib.parse
from typing import Optional


_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_DDG_URL = "https://html.duckduckgo.com/html/"

_SKIP_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com", "tripadvisor", "zomato", "yelp", "foursquare",
    "google.com", "maps.google", "wikipedia.org", "duckduckgo.com",
    "paginas-amarelas", "infopaginas", "guiaempresa", "racius.com",
    "einforma.com", "dnb.com", "trustpilot",
}


# ─── Utilitários ─────────────────────────────────────────────────────────────

def _fetch(url: str, timeout: int = 5) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept": "text/html,*/*;q=0.8",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            if "gzip" in r.headers.get("Content-Encoding", ""):
                raw = _gzip.decompress(raw)
            return raw.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[WEB_SEARCH] fetch failed {url[:60]}: {type(e).__name__}", flush=True)
        return ""


def _ddg_search(query: str, max_results: int = 5) -> list:
    """DuckDuckGo HTML — acessível de IPs cloud, sem API key."""
    params = urllib.parse.urlencode({"q": query, "kl": "pt-pt", "ia": "web"})
    html = _fetch(f"{_DDG_URL}?{params}", timeout=6)
    if not html:
        return []

    results = []

    # Extrai URLs dos resultados
    for m in re.finditer(
        r'class="result__url"[^>]*>\s*(https?://[^\s<"]+)',
        html
    ):
        url = m.group(1).strip().rstrip("/")
        if url and "duckduckgo.com" not in url:
            results.append(url)
            if len(results) >= max_results:
                break

    # Fallback: uddg= links
    if not results:
        for m in re.finditer(r'uddg=(https?[^&"]+)', html):
            try:
                url = urllib.parse.unquote(m.group(1)).rstrip("/")
                if "duckduckgo.com" not in url and url not in results:
                    results.append(url)
                    if len(results) >= max_results:
                        break
            except Exception:
                pass

    return results


def _normalize_phone(raw: str) -> str:
    cleaned = re.sub(r'[\s\-\.\(\)+]', '', raw or "")
    cleaned = re.sub(r'^(00)?351', '', cleaned)
    return cleaned if re.match(r'^[23679]\d{8}$', cleaned) else ""


def _find_phone(text: str) -> Optional[str]:
    for m in re.findall(
        r'(?:(?:\+351|00351)?[\s\-\.]?)([23679]\d{2}[\s\-\.]?\d{3}[\s\-\.]?\d{3})',
        re.sub(r'<[^>]+>', ' ', text)
    ):
        p = _normalize_phone(m)
        if p:
            return p
    return None


_EMAIL_JUNK = {
    'example', 'sentry', 'noreply', 'no-reply', 'schema.org', 'w3.org',
    'facebook.com', 'google.com', 'apple.com', 'twitter.com', 'jquery',
    'wordpress.org', 'cloudflare', 'png', 'jpg', 'gif', 'svg',
}


def _find_email(text: str) -> Optional[str]:
    for c in re.findall(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}',
        text
    ):
        if not any(j in c.lower() for j in _EMAIL_JUNK):
            return c
    return None


# ─── Nível 1: Pesquisa web para encontrar website + contactos ────────────────

def search_web_for_business(name: str, city: str) -> dict:
    """
    Pesquisa DuckDuckGo por '{nome}' '{cidade}' Portugal contacto.
    Devolve dict com: website, telefone, email — apenas os encontrados.
    Timeout total: ~6s (DDG) + 5s (fetch página) = ~11s no pior caso.
    """
    result: dict = {}
    query = f'"{name}" "{city}" Portugal contacto telefone'
    print(f"[WEB_L1] {name[:40]}", flush=True)

    urls = _ddg_search(query, max_results=6)

    for url in urls:
        low = url.lower()
        if any(d in low for d in _SKIP_DOMAINS):
            continue

        # Encontrámos um website candidato
        if not result.get("website"):
            result["website"] = url

        # Fetch para extrair contactos
        page = _fetch(url, timeout=5)
        if page:
            if not result.get("telefone"):
                p = _find_phone(page)
                if p:
                    result["telefone"] = p
            if not result.get("email"):
                e = _find_email(page)
                if e:
                    result["email"] = e

        # Se já temos tudo, pára
        if result.get("website") and result.get("telefone") and result.get("email"):
            break

    return result


# ─── Nível 2: Perfis Instagram e Facebook ────────────────────────────────────

def _ig_from_bio(handle: str) -> dict:
    """
    Tenta extrair contactos da bio pública de Instagram.
    Instagram bloqueia IPs de cloud com frequência — timeout curto.
    """
    html = _fetch(f"https://www.instagram.com/{handle}/", timeout=5)
    if not html:
        return {}

    out: dict = {}

    # JSON embutido no HTML
    bio_m = re.search(r'"biography"\s*:\s*"(.*?)"', html)
    if bio_m:
        bio = bio_m.group(1).replace('\\n', ' ').replace('\\u0026', '&')
        if not out.get("telefone"):
            p = _find_phone(bio)
            if p:
                out["telefone"] = p
        if not out.get("email"):
            e = _find_email(bio)
            if e:
                out["email"] = e

    for pat, field in [
        (r'"public_phone_number"\s*:\s*"([^"]+)"', "telefone"),
        (r'"public_email"\s*:\s*"([^"]+)"', "email"),
        (r'"external_url"\s*:\s*"([^"]+)"', "website_ig"),
    ]:
        m = re.search(pat, html)
        if m and not out.get(field):
            val = m.group(1).replace("\\u0026", "&").strip()
            if val and field == "telefone":
                p = _normalize_phone(val)
                if p:
                    out[field] = p
            elif val:
                out[field] = val

    return out


def _fb_contacts(url: str) -> dict:
    """Raspa página pública de Facebook para extrair contactos."""
    html = _fetch(url, timeout=5)
    if not html:
        return {}
    out: dict = {}
    p = _find_phone(html)
    if p:
        out["telefone"] = p
    e = _find_email(html)
    if e:
        out["email"] = e
    # Website mencionado na página
    w = re.search(
        r'(?:website|site)[^"]*"(https?://(?!facebook)[^"]{5,80})"',
        html, re.IGNORECASE
    )
    if w:
        out["website_fb"] = w.group(1)
    return out


def search_social_profiles(name: str, city: str) -> dict:
    """
    Nível 2 — Localiza perfis Instagram e Facebook pelo nome da empresa.
    Para cada perfil encontrado, extrai contactos da bio/página.
    Devolve dict com: instagram, facebook, tem_instagram, tem_facebook,
                       e eventuais: telefone, email, website.
    """
    result: dict = {}

    # ── Instagram ─────────────────────────────────────────────────────────────
    ig_urls = _ddg_search(f'"{name}" site:instagram.com', max_results=3)
    for url in ig_urls:
        m = re.search(
            r'instagram\.com/([A-Za-z0-9_.]{3,30})/?$',
            url.rstrip("/")
        )
        if not m:
            continue
        handle = m.group(1).lower()
        if handle in ("p", "reel", "explore", "stories", "tv", "reels"):
            continue

        result["instagram"] = f"https://www.instagram.com/{handle}"
        result["tem_instagram"] = True
        print(f"[WEB_L2] Instagram encontrado: @{handle}", flush=True)

        bio = _ig_from_bio(handle)
        for field in ("telefone", "email"):
            if bio.get(field) and not result.get(field):
                result[field] = bio[field]
        if bio.get("website_ig") and not result.get("website"):
            result["website"] = bio["website_ig"]
        break

    # ── Facebook ──────────────────────────────────────────────────────────────
    fb_urls = _ddg_search(f'"{name}" "{city}" site:facebook.com', max_results=3)
    _FB_SKIP = ["/events/", "/groups/", "/photos/", "/videos/",
                "/posts/", "login", "/stories/", "?ref="]
    for url in fb_urls:
        if "facebook.com" not in url:
            continue
        if any(s in url for s in _FB_SKIP):
            continue

        result["facebook"] = url.rstrip("/")
        result["tem_facebook"] = True
        print(f"[WEB_L2] Facebook encontrado: {url[:60]}", flush=True)

        fb = _fb_contacts(url)
        for field in ("telefone", "email"):
            if fb.get(field) and not result.get(field):
                result[field] = fb[field]
        if fb.get("website_fb") and not result.get("website"):
            result["website"] = fb["website_fb"]
        break

    return result
