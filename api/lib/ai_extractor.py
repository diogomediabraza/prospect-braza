"""
Nível 3 — Extracção inteligente de contactos via Claude API.

Dado o HTML de uma página web, usa o Claude Haiku para identificar
contactos mesmo em formatos não-standard (imagens com texto alternativo,
scripts JS, dados estruturados, microformats, etc.).

Custo: ~€0.001–0.003 por empresa (claude-haiku-4-5, modelo mais barato).
Só activa se ANTHROPIC_API_KEY estiver em env vars.
Timeout: 12s para não exceder o budget de 60s do job.
"""
import os
import re
import json
import gzip as _gzip
import urllib.request
from typing import Optional


_MODEL = "claude-haiku-4-5-20251001"
_MAX_HTML_CHARS = 4000   # limita tokens → limita custo
_TIMEOUT = 12


def _clean_html(html: str) -> str:
    """Remove tags, scripts, styles — fica só o texto relevante."""
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:_MAX_HTML_CHARS]


def _normalize_phone(raw: str) -> Optional[str]:
    cleaned = re.sub(r'[\s\-\.\(\)+]', '', raw or "")
    cleaned = re.sub(r'^(00)?351', '', cleaned)
    return cleaned if re.match(r'^[23679]\d{8}$', cleaned) else None


def extract_contacts_with_ai(
    html: str,
    company_name: str,
    city: str,
) -> dict:
    """
    Usa Claude Haiku para extrair contactos de qualquer página web.

    Parâmetros:
        html          — HTML bruto da página
        company_name  — nome da empresa (para contexto)
        city          — cidade (para contexto)

    Devolve dict com zero ou mais campos:
        email, telefone, website, instagram, facebook, linkedin
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {}

    text = _clean_html(html)
    if not text or len(text) < 30:
        return {}

    prompt = (
        f'Analisa o texto desta página da empresa "{company_name}" em {city}, Portugal.\n'
        f'Extrai APENAS contactos reais da empresa. Ignora dados de cookies, analytics e scripts.\n'
        f'Responde EXCLUSIVAMENTE com JSON válido, sem texto adicional.\n\n'
        f'Texto:\n{text}\n\n'
        f'Formato de resposta (usa null se não encontrado):\n'
        f'{{"email":null,"telefone":null,"website":null,'
        f'"instagram":null,"facebook":null,"linkedin":null}}'
    )

    body = json.dumps({
        "model": _MODEL,
        "max_tokens": 150,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            resp = json.loads(r.read().decode("utf-8"))
            raw_text = resp.get("content", [{}])[0].get("text", "")

            j_match = re.search(r'\{[^{}]+\}', raw_text, re.DOTALL)
            if not j_match:
                return {}

            data = json.loads(j_match.group(0))
            result: dict = {}

            # email
            email = data.get("email")
            if email and email not in (None, "null", ""):
                result["email"] = str(email).strip()

            # telefone
            tel = data.get("telefone")
            if tel and tel not in (None, "null", ""):
                p = _normalize_phone(str(tel))
                if p:
                    result["telefone"] = p

            # website
            web = data.get("website")
            if web and web not in (None, "null", ""):
                w = str(web).strip()
                if w.startswith("http"):
                    result["website"] = w

            # redes sociais
            for field in ("instagram", "facebook", "linkedin"):
                val = data.get(field)
                if val and val not in (None, "null", ""):
                    v = str(val).strip()
                    if v.startswith("http") or ("." in v and len(v) > 4):
                        result[field] = v

            if result:
                print(
                    f"[AI_L3] '{company_name}': encontrou {list(result.keys())}",
                    flush=True
                )
            return result

    except Exception as e:
        print(f"[AI_L3] Erro '{company_name}': {type(e).__name__}: {e}", flush=True)
        return {}
