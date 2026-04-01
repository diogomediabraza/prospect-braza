"""
GET  /api/jobs — list all jobs
POST /api/jobs — create a new scraping job
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
from lib.scraper import scrape_all_sources, check_digital_presence, calculate_scores

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
    Uses ThreadPoolExecutor to enrich all company websites in parallel,
    making the most of Vercel's 60-second serverless limit.
    """
    try:
        sb_update("jobs", {"id": f"eq.{job_id}"}, {"status": "a_correr", "progresso": 0})

        # Step 1: Collect raw companies from all sources
        raw_companies = scrape_all_sources(nicho, localidade, max_results)
        total = len(raw_companies)

        if total == 0:
            sb_update("jobs", {"id": f"eq.{job_id}"},
                      {"status": "concluido", "progresso": 100,
                       "total_encontrados": 0, "data_fim": datetime.now(timezone.utc).isoformat()})
            return

        sb_update("jobs", {"id": f"eq.{job_id}"}, {"progresso": 10})

        # Step 2: Enrich all websites in PARALLEL (10 threads, 45s timeout)
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
                # Progress: 10% -> 80% during enrichment
                progress = 10 + int((done / total) * 70)
                sb_update("jobs", {"id": f"eq.{job_id}"}, {"progresso": progress})

        sb_update("jobs", {"id": f"eq.{job_id}"}, {"progresso": 85})

        # Step 3: Build rows and insert into DB
        inserted = 0
        for i, company in enumerate(raw_companies):
            try:
                presence = presence_map.get(i, dict(_EMPTY_PRESENCE))
                fonte = company.get("fonte_raw", "OpenStreetMap")

                full_data = {
                    **company,
                    **presence,
                    "nicho": company.get("nicho", nicho),
                    "localidade": company.get("localidade", localidade),
                    "status": "novo",
                    "fonte": fonte,
                }

                # Source data takes priority over website-extracted contacts
                for field in ("email", "telefone", "instagram", "facebook", "linkedin"):
                    original = company.get(field)
                    if original and str(original).strip():
                        full_data[field] = original

                full_data.setdefault("tem_facebook", bool(full_data.get("facebook")))
                full_data.setdefault("tem_instagram", bool(full_data.get("instagram")))
                full_data.setdefault("tem_linkedin", bool(full_data.get("linkedin")))
                full_data.setdefault("tem_youtube", False)
                full_data.setdefault("tem_tiktok", False)
                full_data.setdefault("instagram", None)
                full_data.setdefault("facebook", None)
                full_data.setdefault("linkedin", None)

                scores = calculate_scores(full_data)
                full_data.update(scores)

                # Helper: safely convert to string, treating None as empty
                def _s(val, maxlen=255):
                    if val is None:
                        return None
                    s = str(val).strip()
                    if not s or s.lower() == "none":
                        return None
                    return s[:maxlen]

                row = {
                    "id": str(uuid.uuid4()),
                    "nome": _s(full_data.get("nome"), 255) or "",
                    "nicho": _s(full_data.get("nicho"), 100) or "",
                    "localidade": _s(full_data.get("localidade"), 100) or "",
                    "morada": _s(full_data.get("morada"), 255),
                    "codigo_postal": _s(full_data.get("codigo_postal"), 20),
                    "telefone": _s(full_data.get("telefone"), 50),
                    "email": _s(full_data.get("email"), 255),
                    "website": _s(full_data.get("website"), 255),
                    "instagram": _s(full_data.get("instagram"), 255),
                    "facebook": _s(full_data.get("facebook"), 255),
                    "linkedin": _s(full_data.get("linkedin"), 255),
                    "tem_website": bool(full_data.get("tem_website")),
                    "tem_loja_online": bool(full_data.get("tem_loja_online")),
                    "tem_facebook": bool(full_data.get("tem_facebook")),
                    "tem_instagram": bool(full_data.get("tem_instagram")),
                    "tem_linkedin": bool(full_data.get("tem_linkedin")),
                    "tem_youtube": bool(full_data.get("tem_youtube")),
                    "tem_tiktok": bool(full_data.get("tem_tiktok")),
                    "tem_google_ads": bool(full_data.get("tem_google_ads")),
                    "tem_facebook_ads": bool(full_data.get("tem_facebook_ads")),
                    "tem_gtm": bool(full_data.get("tem_gtm")),
                    "tem_ga4": bool(full_data.get("tem_ga4")),
                    "tem_pixel_meta": bool(full_data.get("tem_pixel_meta")),
                    "score_maturidade_digital": full_data.get("score_maturidade_digital"),
                    "score_oportunidade_comercial": full_data.get("score_oportunidade_comercial"),
                    "score_prioridade_sdr": full_data.get("score_prioridade_sdr"),
                    "status": "novo",
                    "fonte": fonte,
                }

                sb_insert("companies", row,
                          on_conflict="nome,localidade",
                          ignore_duplicates=True)
                inserted += 1
            except Exception:
                pass

        sb_update("jobs", {"id": f"eq.{job_id}"},
                  {"status": "concluido", "progresso": 100,
                   "total_encontrados": inserted, "data_fim": datetime.now(timezone.utc).isoformat()})

    except Exception as e:
        sb_update("jobs", {"id": f"eq.{job_id}"},
                  {"status": "erro", "mensagem_erro": str(e)[:500], "data_fim": datetime.now(timezone.utc).isoformat()})


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
            nicho = data.get("nicho", "").strip()
            localidade = data.get("localidade", "").strip()
            max_resultados = min(int(data.get("max_resultados", 50)), 200)

            if not nicho or not localidade:
                status, headers, body = error_response("nicho e localidade são obrigatórios")
                send_response(self, status, headers, body)
                return

            job_id = str(uuid.uuid4())

            sb_insert("jobs", {
                "id": job_id,
                "nicho": nicho,
                "localidade": localidade,
                "max_resultados": max_resultados,
                "status": "pendente",
                "progresso": 0,
                "total_encontrados": 0,
            })

            run_scraping_job(job_id, nicho, localidade, max_resultados)

            updated = sb_select("jobs", filters={"id": f"eq.{job_id}"}, limit=1)
            job = updated[0] if updated else {"id": job_id, "status": "concluido"}
            status, headers, body = json_response(job, 201)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
