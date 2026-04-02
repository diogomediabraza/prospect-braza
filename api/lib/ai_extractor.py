"""
Nível 3 — Extracção inteligente de contactos via IA.

Tenta Claude Haiku primeiro (ANTHROPIC_API_KEY).
Se não disponível, tenta GPT-4o mini (OPENAI_API_KEY) como fallback.

Custo: ~€0.001–0.003 por empresa.
Só activa se pelo menos uma das API keys estiver em env vars.
Timeout: 12s para não exceder o budget de 60s do job.
"""
import os
import re
import json
import urllib.request
from typing import Optional


_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
_OPENAI_MODEL    = "gpt-4o-mini"
_MAX_HTML_CHARS  = 4000   # limita tokens → limita custo
_TIMEOUT         = 12


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


def _parse_ai_response(raw_text: str, company_name: str) -> dict:
    """Converte resposta de texto da IA em dict de contactos."""
    j_match = re.search(r'\{[^{}]+\}', raw_text, re.DOTALL)
    if not j_match:
        return {}

    data = json.loads(j_match.group(0))
    result: dict = {}

    email = data.get("email")
    if email and email not in (None, "null", ""):
        result["email"] = str(email).strip()

    tel = data.get("telefone")
    if tel and tel not in (None, "null", ""):
        p = _normalize_phone(str(tel))
        if p:
            result["telefone"] = p

    web = data.get("website")
    if web and web not in (None, "null", ""):
        w = str(web).strip()
        if w.startswith("http"):
            result["website"] = w

    for field in ("instagram", "facebook", "linkedin"):
        val = data.get(field)
        if val and val not in (None, "null", ""):
            v = str(val).strip()
            if v.startswith("http") or ("." in v and len(v) > 4):
                result[field] = v

    if result:
        print(f"[AI_L3] '{company_name}': encontrou {list(result.keys())}", flush=True)
    return result


def _build_prompt(text: str, company_name: str, city: str) -> str:
    return (
        f'Analisa o texto desta página da empresa "{company_name}" em {city}, Portugal.\n'
        f'Extrai APENAS contactos reais da empresa. Ignora dados de cookies, analytics e scripts.\n'
        f'Responde EXCLUSIVAMENTE com JSON válido, sem texto adicional.\n\n'
        f'Texto:\n{text}\n\n'
        f'Formato de resposta (usa null se não encontrado):\n'
        f'{{"email":null,"telefone":null,"website":null,'
        f'"instagram":null,"facebook":null,"linkedin":null}}'
    )


def _extract_with_claude(prompt: str, api_key: str) -> str:
    """Chama Claude Haiku e devolve o texto da resposta."""
    body = json.dumps({
        "model": _ANTHROPIC_MODEL,
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
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        resp = json.loads(r.read().decode("utf-8"))
        return resp.get("content", [{}])[0].get("text", "")


def _extract_with_openai(prompt: str, api_key: str) -> str:
    """Chama GPT-4o mini e devolve o texto da resposta."""
    body = json.dumps({
        "model": _OPENAI_MODEL,
        "max_tokens": 150,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        resp = json.loads(r.read().decode("utf-8"))
        return resp["choices"][0]["message"]["content"]


def extract_contacts_with_ai(
    html: str,
    company_name: str,
    city: str,
) -> dict:
    """
    Extrai contactos de qualquer página web usando IA.

    Ordem de preferência:
      1. Claude Haiku  (se ANTHROPIC_API_KEY definido)
      2. GPT-4o mini   (se OPENAI_API_KEY definido, como fallback)

    Parâmetros:
        html          — HTML bruto da página
        company_name  — nome da empresa (para contexto)
        city          — cidade (para contexto)

    Devolve dict com zero ou mais campos:
        email, telefone, website, instagram, facebook, linkedin
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key    = os.environ.get("OPENAI_API_KEY", "")

    if not anthropic_key and not openai_key:
        return {}

    text = _clean_html(html)
    if not text or len(text) < 30:
        return {}

    prompt = _build_prompt(text, company_name, city)

    # ── Tentativa 1: Claude Haiku ─────────────────────────────────────────────
    if anthropic_key:
        try:
            raw = _extract_with_claude(prompt, anthropic_key)
            result = _parse_ai_response(raw, company_name)
            if result:
                return result
            # Sem resultado — tenta OpenAI se disponível
        except Exception as e:
            print(f"[AI_L3/Claude] '{company_name}': {type(e).__name__}", flush=True)

    # ── Tentativa 2: GPT-4o mini (fallback) ──────────────────────────────────
    if openai_key:
        try:
            raw = _extract_with_openai(prompt, openai_key)
            return _parse_ai_response(raw, company_name)
        except Exception as e:
            print(f"[AI_L3/OpenAI] '{company_name}': {type(e).__name__}", flush=True)

    return {}
