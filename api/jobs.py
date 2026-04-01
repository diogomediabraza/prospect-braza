"""
GET  /api/jobs — list all jobs
POST /api/jobs — create a new scraping job

CHANGELOG:
- run_scraping_job() agora passa job_id para cada company inserida
- Leads classificados como 'lixo' NÃO são inseridos na base
- Novos campos gravados: score_qualidade_lead, classificacao_lead,
  motivo_descarte, confianca_email, confianca_telefone, fontes_encontradas
- total_validos e total_descartados actualizados no job
- max_resultados aumentado para 200
"""
from http.server import BaseHTTPRequestHandler
import sys
import os
import json
import uuid
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

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
    """Worker: fetch digital presence for one company. Returns presence dict."""
    website = company.get("website")
    if not website:
        return dict(_EMPTY_PRESENCE)
    try:
        return check_digital_presence(website)
    except Exception:
        return {**_EMPTY_PRESENCE, "tem_website": True}


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
        sb_update("jobs", {"id": f"eq.{job_id}"}, {"status": "a_correr", "progresso": 0})

        # ── ETAPA 1: Descoberta ───────────────────────────────────────────────
        log(f"[JOB {job_id[:8]}] Etapa 1: Descoberta de candidatos...")
        raw_companies = scrape_all_sources(nicho, localidade, max_results)
        total = len(raw_companies)
        log(f"[JOB {job_id[:8]}] {total} candidatos encontrados antes de deduplicação")

        if total == 0:
            sb_update("jobs", {"id": f"eq.{job_id}"},
                      {"status": "concluido", "progresso": 100,
                       "total_encontrados": 0, "total_validos": 0,
                       "total_descartados": 0,
                       "logs_resumidos": json.dumps(logs),
                       "data_fim": datetime.now(timezone.utc).isoformat()})
            return

        sb_update("jobs", {"id": f"eq.{job_id}"}, {"progresso": 10})

        # ── ETAPA 2: Enriquecimento paralelo ──────────────────────────────────
        log(f"[JOB {job_id[:8]}] Etapa 2: Enriquecimento paralelo de {total} candidatos...")
        presence_map: dict = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(_enrich, company): i
                for i, company in enumerate(raw_companies)
            }
            done = 0
            for future in as_completed(futures, timeout=45):
                i = futures[future]
                try:
                    presence_map[i] = future.result()
                except Exception:
                    presence_map[i] = dict(_EMPTY_PRESENCE)
                done += 1
                progress = 10 + int((done / total) * 70)
                sb_update("jobs", {"id": f"eq.{job_id}"}, {"progresso": progress})

        sb_update("jobs", {"id": f"eq.{job_id}"}, {"progresso": 85})

        # ── ETAPA 3: Classificação e inserção ─────────────────────────────────
        log(f"[JOB {job_id[:8]}] Etapa 3: Score, classificação e inserção...")
        inserted    = 0
        descartados = 0

        for i, company in enumerate(raw_companies):
            try:
                presence = presence_map.get(i, dict(_EMPTY_PRESENCE))
                fonte    = company.get("fonte_raw", "OSM Overpass")
                fontes   = company.get("_fontes", [fonte])

                full_data = {
                    **company,
                    **presence,
                    "nicho":      company.get("nicho", nicho),
                    "localidade": company.get("localidade", localidade),
                    "status":     "novo",
                    "fonte":      fonte,
                }

                # Dados originais da fonte têm prioridade sobre os extraídos do site
                for field in ("email", "telefone", "instagram", "facebook", "linkedin"):
                    original = company.get(field)
                    if original and str(original).strip():
                        full_data[field] = original

                # Garantir que confiança do telefone é 'alta' se veio de API
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

                # Calcular scores
                scores = calculate_scores(full_data)
                full_data.update(scores)

                # Classificar o lead
                classificacao, motivo_descarte = classify_lead(full_data)

                # LIXO não é inserido — apenas contado
                if classificacao == "lixo":
                    descartados += 1
                    log(f"[LIXO] '{full_data.get('nome', '?')}': {motivo_descarte}")
                    continue

                # Construir row com todos os campos novos
                fontes_array = fontes if isinstance(fontes, list) else [fontes]

                row = {
                    "id":                           str(uuid.uuid4()),
                    "job_id":                       job_id,           # NOVO: FK
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
                    "score_qualidade_lead":         full_data.get("score_qualidade_lead", 0),     # NOVO
                    "score_maturidade_digital":     full_data.get("score_maturidade_digital"),
                    "score_oportunidade_comercial": full_data.get("score_oportunidade_comercial"),
                    "score_prioridade_sdr":         full_data.get("score_prioridade_sdr"),
                    "classificacao_lead":           classificacao,                                 # NOVO
                    "motivo_descarte":              motivo_descarte,                              # NOVO
                    "confianca_email":              full_data.get("confianca_email", "desconhecida"),  # NOVO
                    "confianca_telefone":           full_data.get("confianca_telefone", "desconhecida"),  # NOVO
                    "fontes_encontradas":           fontes_array,                                 # NOVO
                    "ultima_validacao":             datetime.now(timezone.utc).isoformat(),       # NOVO
                    "status":                       "novo",
                    "fonte":                        fonte,
                }

                sb_insert("companies", row,
                          on_conflict="nome,localidade",
                          ignore_duplicates=True)
                inserted += 1

            except Exception as ex:
                log(f"[ERRO] Lead {i}: {ex}")

        log(f"[JOB {job_id[:8]}] Concluído: {inserted} válidos, {descartados} descartados como lixo")

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
