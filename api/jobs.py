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

sys.path.insert(0, os.path.dirname(__file__))

from lib.db import sb_select, sb_insert, sb_update
from lib.helpers import json_response, error_response, send_response, parse_body
from lib.scraper import scrape_all_sources, check_digital_presence, calculate_scores


def _has_min_contact_data(company: dict) -> bool:
    """Return True if the company has at least 2 of: telefone, email, website, instagram."""
    fields = ["telefone", "email", "website", "instagram"]
    count = sum(1 for f in fields if company.get(f) and str(company[f]).strip())
    return count >= 2


def run_scraping_job(job_id: str, nicho: str, localidade: str, max_results: int):
    """Run scraping job synchronously (Vercel kills daemon threads after response)."""
    try:
        # Mark as running
        sb_update("jobs", {"id": f"eq.{job_id}"}, {"status": "a_correr", "progresso": 0})

        # Fetch more raw results so after quality filtering we still have enough
        raw_fetch = max(max_results * 4, 80)
        raw_companies = scrape_all_sources(nicho, localidade, raw_fetch)

        # Quality filter: keep only companies with at least 2 contact fields
        qualified = [c for c in raw_companies if _has_min_contact_data(c)]

        # If quality filter leaves too few, lower the bar to 1 contact field
        if len(qualified) < max(5, max_results // 4):
            qualified = [c for c in raw_companies if any(
                c.get(f) and str(c[f]).strip() for f in ["telefone", "email", "website", "instagram"]
            )]

        companies_to_insert = qualified[:max_results]
        total = len(companies_to_insert)
        inserted = 0

        for i, company in enumerate(companies_to_insert):
            try:
                presence = check_digital_presence(company.get("website"))
                fonte = company.get("fonte_raw", "OpenStreetMap")
                full_data = {
                    **company,
                    **presence,
                    "nicho": company.get("nicho", nicho),
                    "localidade": company.get("localidade", localidade),
                    "status": "novo",
                    "fonte": fonte,
                }
                # Source data (OSM / Foursquare / etc.) takes priority over
                # website-extracted values for all contact fields.
                # Website-extracted values only fill in fields that are missing.
                for field in ("email", "telefone", "instagram", "facebook", "linkedin"):
                    original = company.get(field)
                    if original and str(original).strip():
                        full_data[field] = original
                    # else: keep website-extracted value already in full_data

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

                row = {
                    "id": str(uuid.uuid4()),
                    "nome": str(full_data.get("nome", ""))[:255],
                    "nicho": str(full_data.get("nicho", ""))[:100],
                    "localidade": str(full_data.get("localidade", ""))[:100],
                    "morada": str(full_data.get("morada", ""))[:255],
                    "codigo_postal": str(full_data.get("codigo_postal", ""))[:20],
                    "telefone": str(full_data.get("telefone", ""))[:50],
                    "email": str(full_data.get("email", ""))[:255],
                    "website": str(full_data.get("website", ""))[:255],
                    "instagram": str(full_data.get("instagram") or "")[:255] or None,
                    "facebook": str(full_data.get("facebook") or "")[:255] or None,
                    "linkedin": str(full_data.get("linkedin") or "")[:255] or None,
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

                # Insert, ignore on duplicate (nome+localidade)
                sb_insert(
                    "companies", row,
                    on_conflict="nome,localidade",
                    ignore_duplicates=True
                )
                inserted += 1
            except Exception:
                pass

            progress = int(((i + 1) / max(total, 1)) * 100)
            sb_update(
                "jobs", {"id": f"eq.{job_id}"},
                {"progresso": progress, "total_encontrados": inserted}
            )

        sb_update(
            "jobs", {"id": f"eq.{job_id}"},
            {
                "status": "concluido",
                "progresso": 100,
                "total_encontrados": inserted,
                "data_fim": "now()",
            }
        )

    except Exception as e:
        sb_update(
            "jobs", {"id": f"eq.{job_id}"},
            {"status": "erro", "mensagem_erro": str(e)[:500], "data_fim": "now()"}
        )


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
            # Cap at 50 — keeps synchronous execution within Vercel's 60s limit
            max_resultados = min(int(data.get("max_resultados", 20)), 50)

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

            # Run synchronously — Vercel kills daemon threads after the response
            # is sent, so background threading does not work on serverless.
            run_scraping_job(job_id, nicho, localidade, max_resultados)

            # Return the final job state
            updated = sb_select("jobs", filters={"id": f"eq.{job_id}"}, limit=1)
            job = updated[0] if updated else {"id": job_id, "status": "concluido"}

            status, headers, body = json_response(job, 201)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
