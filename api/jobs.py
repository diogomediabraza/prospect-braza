"""
GET  /api/jobs — list all jobs
POST /api/jobs — create a new scraping job

CHANGELOG:
- run_scraping_job() agora passa job_id para cada company inserida
- Leads classificados como 'lixo' ou 'fraco' NÃO são inseridos na base
  (apenas 'bom' score≥35 e 'excelente' score≥60 são guardados)
- Busca 4× mais candidatos brutos para garantir pool suficiente
- Para assim que atinge max_results leads de qualidade
- Novos campos gravados: score_qualidade_lead, classificacao_lead,
  motivo_descarte, confianca_email, confianca_telefone, fontes_encontradas
- total_validos e total_descartados actualizados no job
- max_resultados aumentado para 200
- [DEEP ENRICH] Nível 1: DuckDuckGo para empresas sem website
- [DEEP ENRICH] Nível 2: pesquisa Instagram/Facebook por nome
- [DEEP ENRICH] Nível 3: Claude IA extrai contactos de qualquer página
"""

# Classificações mínimas aceites — abaixo disto o lead é descartado
_QUALIDADE_MINIMA = {"bom", "excelente"}  # score_qualidade_lead ≥ 35
from http.server import BaseHTTPRequestHandler
import sys
import os
import json
import uuid
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# Orçamento total do job em segundos.
# Vercel Hobby: maxDuration=60s — deixamos 10s de margem.
_JOB_BUDGET = 50

sys.path.insert(0, os.path.dirname(__file__))

from lib.db import sb_select, sb_insert, sb_update
from lib.helpers import json_response, error_response, send_response, parse_body
from lib.scraper import scrape_all_sources, check_digital_presence, calculate_scores, classify_lead

_EMPTY_PRESENCE = {
    "tem_website": False, "tem_loja_online": False,
    "tem_gtm": False, "tem_ga4": False,
    "tem_pixel_meta": False, "tem_google_ads": False,
    "tem_facebook_ads": False,
    "tem_instagram": False, "tem_facebook": False, "tem_linkedin": False,
    "instagram": None, "facebook": None, "linkedin": None,
    "email": None, "telefone": None,
    "confianca_email": "desconhecida", "confianca_telefone": "desconhecida",
}

_EMPTY_PRESENCE = {
    "tem_website": False, "tem_loja_online": False,
    "tem_gtm": False, "tem_ga4": False,
    "tem_pixel_meta": False, "tem_google_ads": False,
    "tem_facebook_ads": False,
    "tem_instagram": False, "tem_facebook": False, "tem_linkedin": False,
    "instagram": None, "facebook": None, "linkedin": None,
    "email": None, "telefone": None,
}

def _enrich(company: dict) -> dict:
    """
    Worker: enriquecimento completo de uma empresa.

    Nível 0 (sempre): check_digital_presence no website original.
    Nível 1 (se sem website ou sem contactos): DuckDuckGo para encontrar website.
    Nível 2 (se sem Instagram/Facebook): pesquisa DDG site:instagram/facebook.
    Nível 3 (se sem email+telefone e ANTHROPIC_API_KEY definido): Claude IA.

    Timeouts curtos para caber no budget de 60s do Vercel Hobby.
    Falha silenciosa — nunca propaga excepção.
    """
    name     = company.get("nome", "")
    city     = company.get("localidade", "")
    website  = company.get("website")

    # ── Nível 0: Website original ─────────────────────────────────────────────
    if website:
        try:
            presence = check_digital_presence(website)
        except Exception:
            presence = {**_EMPTY_PRESENCE, "tem_website": True}
    else:
        presence = dict(_EMPTY_PRESENCE)

    # ── Nível 1: Pesquisa web (empresa sem website ou sem contactos) ──────────
    sem_contacto = not presence.get("email") and not presence.get("telefone")
    if (not website or sem_contacto) and name and city:
        try:
            from lib.source_web_search import search_web_for_business
            web = search_web_for_business(name, city)
            # Preenche campos em falta
            for field in ("telefone", "email"):
                if web.get(field) and not presence.get(field):
                    presence[field] = web[field]
            # Se encontrou website novo, faz check_digital_presence
            if web.get("website") and not website:
                try:
                    new_p = check_digital_presence(web["website"])
                    presence["tem_website"] = True
                    presence["website_encontrado"] = web["website"]
                    for field in ("email", "telefone", "instagram", "facebook",
                                  "linkedin", "tem_instagram", "tem_facebook",
                                  "tem_linkedin", "tem_gtm", "tem_ga4",
                                  "tem_pixel_meta", "tem_google_ads",
                                  "tem_loja_online", "confianca_email",
                                  "confianca_telefone"):
                        if new_p.get(field) and not presence.get(field):
                            presence[field] = new_p[field]
                except Exception:
                    pass
        except Exception as e:
            print(f"[ENRICH L1] '{name}': {type(e).__name__}", flush=True)

    # ── Nível 2: Redes sociais (sem Instagram e sem Facebook) ─────────────────
    sem_social = not presence.get("instagram") and not presence.get("facebook")
    if sem_social and name and city:
        try:
            from lib.source_web_search import search_social_profiles
            social = search_social_profiles(name, city)
            for field in ("instagram", "facebook", "tem_instagram",
                          "tem_facebook", "telefone", "email"):
                if social.get(field) and not presence.get(field):
                    presence[field] = social[field]
            # Website encontrado via redes sociais
            if social.get("website") and not presence.get("tem_website"):
                presence["website_encontrado"] = social["website"]
        except Exception as e:
            print(f"[ENRICH L2] '{name}': {type(e).__name__}", flush=True)

    # ── Nível 3: IA Claude — extracção inteligente (último recurso) ───────────
    sem_tudo = not presence.get("email") and not presence.get("telefone")
    if sem_tudo and os.environ.get("ANTHROPIC_API_KEY"):
        # Tenta encontrar algum HTML para dar à IA
        url_para_ia = (
            website or
            presence.get("website_encontrado") or
            presence.get("instagram") or
            presence.get("facebook")
        )
        if url_para_ia:
            try:
                from lib.scraper import fetch_url
                from lib.ai_extractor import extract_contacts_with_ai
                html = fetch_url(url_para_ia, timeout=6)
                if html:
                    ai = extract_contacts_with_ai(html, name, city)
                    for field in ("email", "telefone", "website",
                                  "instagram", "facebook", "linkedin"):
                        if ai.get(field) and not presence.get(field):
                            presence[field] = ai[field]
                    # Actualizar booleanos de redes sociais
                    if ai.get("instagram"):
                        presence["tem_instagram"] = True
                    if ai.get("facebook"):
                        presence["tem_facebook"] = True
                    if ai.get("linkedin"):
                        presence["tem_linkedin"] = True
            except Exception as e:
                print(f"[ENRICH L3] '{name}': {type(e).__name__}", flush=True)

    # Propaga website encontrado para o campo principal (para scoring)
    if presence.get("website_encontrado") and not company.get("website"):
        company["website"] = presence["website_encontrado"]

    return presence


def run_scraping_job(job_id: str, nicho: str, localidade: str, max_results: int):
    """
    Run scraping job synchronously.
    Uses ThreadPoolExecutor to enrich all company websites in parallel.

    CORRIGIDO:
    - Passa job_id a cada lead inserido
    - Não insere leads classificados como 'lixo'
    - Guarda total_validos e total_descartados no job
    - Guarda classificacao_lead, score_qualidade_lead, motivo_descarte
    """
    logs = []

    def log(msg):
        print(msg, flush=True)
        logs.append(msg)

    try:
        t_start = time.time()   # relógio de parede — controla o orçamento
        sb_update("jobs", {"id": f"eq.{job_id}"}, {"status": "a_correr", "progresso": 0})

        # ── ETAPA 1: Descoberta ───────────────────────────────────────────────
        # Busca 4× mais candidatos para garantir leads de qualidade suficientes
        # (muitos serão filtrados como 'fraco' ou 'lixo' na etapa 3)
        pool_size = min(max_results * 4, 400)
        log(f"[JOB {job_id[:8]}] Etapa 1: Descoberta — a pedir {pool_size} candidatos para garantir {max_results} de qualidade...")
        raw_companies = scrape_all_sources(nicho, localidade, pool_size)
        total = len(raw_companies)
        log(f"[JOB {job_id[:8]}] {total} candidatos encontrados antes de filtragem")

        if total == 0:
            sb_update("jobs", {"id": f"eq.{job_id}"},
                      {"status": "concluido", "progresso": 100,
                       "total_encontrados": 0, "total_validos": 0,
                       "total_descartados": 0,
                       "logs_resumidos": json.dumps(logs),
                       "data_fim": datetime.now(timezone.utc).isoformat()})
            return

        sb_update("jobs", {"id": f"eq.{job_id}"}, {"progresso": 10})

        # ── ETAPAS 2+3 unificadas: enriquecer → classificar → inserir de imediato ──
        # Cada empresa é inserida assim que fica pronta, sem esperar pelas outras.
        # Se a função for morta pelo Vercel, os leads já inseridos ficam guardados.
        enrich_deadline = t_start + (_JOB_BUDGET - 8)   # reserva 8s para overhead final
        log(f"[JOB {job_id[:8]}] Etapa 2+3: enriquecer+inserir {total} candidatos (deadline em {int(enrich_deadline - time.time())}s)...")
        inserted    = 0
        descartados = 0
        done        = 0

        def _score_and_insert(company: dict, presence: dict) -> bool:
            """Classifica e insere imediatamente. Devolve True se inserido."""
            nonlocal inserted, descartados
            fonte  = company.get("fonte_raw", "OSM Overpass")
            fontes = company.get("_fontes", [fonte])

            full_data = {
                **company, **presence,
                "nicho": company.get("nicho", nicho),
                "localidade": company.get("localidade", localidade),
                "status": "novo", "fonte": fonte,
            }
            for field in ("email", "telefone", "instagram", "facebook", "linkedin"):
                original = company.get(field)
                if original and str(original).strip():
                    full_data[field] = original

            fonte_lower = fonte.lower()
            if any(f in fonte_lower for f in ("foursquare", "here places", "google places", "osm")):
                if full_data.get("telefone"):
                    full_data["confianca_telefone"] = "alta"

            full_data.setdefault("tem_facebook",  bool(full_data.get("facebook")))
            full_data.setdefault("tem_instagram", bool(full_data.get("instagram")))
            full_data.setdefault("tem_linkedin",  bool(full_data.get("linkedin")))
            full_data.setdefault("tem_youtube",   False)
            full_data.setdefault("tem_tiktok",    False)
            full_data.setdefault("instagram",     None)
            full_data.setdefault("facebook",      None)
            full_data.setdefault("linkedin",      None)

            scores = calculate_scores(full_data)
            full_data.update(scores)
            classificacao, motivo_descarte = classify_lead(full_data)

            if classificacao not in _QUALIDADE_MINIMA:
                descartados += 1
                return False

            if inserted >= max_results:
                return False

            fontes_array = fontes if isinstance(fontes, list) else [fontes]
            row = {
                "id":                           str(uuid.uuid4()),
                "job_id":                       job_id,
                "nome":                         str(full_data.get("nome", ""))[:255],
                "nicho":                        str(full_data.get("nicho", ""))[:100],
                "localidade":                   str(full_data.get("localidade", ""))[:100],
                "morada":                       str(full_data.get("morada", ""))[:255],
                "codigo_postal":                str(full_data.get("codigo_postal", ""))[:20],
                "telefone":                     str(full_data.get("telefone", ""))[:50],
                "email":                        str(full_data.get("email", ""))[:255],
                "website":                      str(full_data.get("website", ""))[:255],
                "instagram":                    str(full_data.get("instagram") or "")[:255] or None,
                "facebook":                     str(full_data.get("facebook") or "")[:255] or None,
                "linkedin":                     str(full_data.get("linkedin") or "")[:255] or None,
                "tem_website":                  bool(full_data.get("tem_website")),
                "tem_loja_online":              bool(full_data.get("tem_loja_online")),
                "tem_facebook":                 bool(full_data.get("tem_facebook")),
                "tem_instagram":                bool(full_data.get("tem_instagram")),
                "tem_linkedin":                 bool(full_data.get("tem_linkedin")),
                "tem_youtube":                  bool(full_data.get("tem_youtube")),
                "tem_tiktok":                   bool(full_data.get("tem_tiktok")),
                "tem_google_ads":               bool(full_data.get("tem_google_ads")),
                "tem_facebook_ads":             bool(full_data.get("tem_facebook_ads")),
                "tem_gtm":                      bool(full_data.get("tem_gtm")),
                "tem_ga4":                      bool(full_data.get("tem_ga4")),
                "tem_pixel_meta":               bool(full_data.get("tem_pixel_meta")),
                "score_qualidade_lead":         full_data.get("score_qualidade_lead", 0),
                "score_maturidade_digital":     full_data.get("score_maturidade_digital"),
                "score_oportunidade_comercial": full_data.get("score_oportunidade_comercial"),
                "score_prioridade_sdr":         full_data.get("score_prioridade_sdr"),
                "classificacao_lead":           classificacao,
                "motivo_descarte":              motivo_descarte,
                "confianca_email":              full_data.get("confianca_email", "desconhecida"),
                "confianca_telefone":           full_data.get("confianca_telefone", "desconhecida"),
                "fontes_encontradas":           fontes_array,
                "ultima_validacao":             datetime.now(timezone.utc).isoformat(),
                "status":                       "novo",
                "fonte":                        fonte,
            }
            sb_insert("companies", row, on_conflict="nome,localidade", ignore_duplicates=True)
            inserted += 1
            return True

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_company = {}
            for i, company in enumerate(raw_companies):
                if time.time() >= enrich_deadline or inserted >= max_results:
                    break
                future_to_company[executor.submit(_enrich, company)] = company

            remaining = max(3.0, enrich_deadline - time.time())
            try:
                for future in as_completed(future_to_company, timeout=remaining):
                    if inserted >= max_results:
                        break
                    company = future_to_company[future]
                    try:
                        presence = future.result()
                    except Exception:
                        presence = dict(_EMPTY_PRESENCE)
                    try:
                        _score_and_insert(company, presence)
                    except Exception as ex:
                        log(f"[ERRO] {company.get('nome','?')}: {ex}")
                    done += 1
                    progress = 10 + int((done / max(len(future_to_company), 1)) * 85)
                    sb_update("jobs", {"id": f"eq.{job_id}"},
                              {"progresso": progress, "total_validos": inserted})
            except Exception:
                log(f"[JOB {job_id[:8]}] Timeout — {done} processados, {inserted} inseridos")

        log(f"[JOB {job_id[:8]}] Concluído: {inserted} válidos, {descartados} descartados")

        sb_update("jobs", {"id": f"eq.{job_id}"},
                  {"status": "concluido", "progresso": 100,
                   "total_encontrados": inserted + descartados,
                   "total_validos":     inserted,        # NOVO
                   "total_descartados": descartados,     # NOVO
                   "logs_resumidos":    json.dumps(logs[-50:]),  # últimos 50 logs
                   "data_fim":          datetime.now(timezone.utc).isoformat()})

    except Exception as e:
        sb_update("jobs", {"id": f"eq.{job_id}"},
                  {"status": "erro",
                   "mensagem_erro": str(e)[:500],
                   "logs_resumidos": json.dumps(logs[-20:]),
                   "data_fim": datetime.now(timezone.utc).isoformat()})


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def do_GET(self):
        try:
            jobs = sb_select("jobs", order="data_inicio.desc", limit=100)
            status, headers, body = json_response(jobs)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)
        send_response(self, status, headers, body)

    def do_POST(self):
        try:
            data = parse_body(self)
            nicho        = data.get("nicho", "").strip()
            localidade   = data.get("localidade", "").strip()
            # CORRIGIDO: limite aumentado de 50 para 200
            max_resultados = min(int(data.get("max_resultados", 50)), 200)

            if not nicho or not localidade:
                status, headers, body = error_response("nicho e localidade são obrigatórios")
                send_response(self, status, headers, body)
                return

            job_id = str(uuid.uuid4())

            sb_insert("jobs", {
                "id":              job_id,
                "nicho":           nicho,
                "localidade":      localidade,
                "max_resultados":  max_resultados,
                "status":          "pendente",
                "progresso":       0,
                "total_encontrados": 0,
                "total_validos":   0,
                "total_descartados": 0,
            })

            run_scraping_job(job_id, nicho, localidade, max_resultados)

            updated = sb_select("jobs", filters={"id": f"eq.{job_id}"}, limit=1)
            job     = updated[0] if updated else {"id": job_id, "status": "concluido"}
            status, headers, body = json_response(job, 201)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
