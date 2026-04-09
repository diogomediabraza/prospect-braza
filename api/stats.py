"""GET /api/stats — dashboard statistics."""
from http.server import BaseHTTPRequestHandler
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.db import sb_select
from lib.helpers import json_response, error_response, send_response


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def do_GET(self):
        try:
            # Fetch all companies with only the columns we need for stats
            companies = sb_select(
                "prospect_companies",
                select="tem_website,tem_instagram,tem_facebook,score_oportunidade_comercial,crm_lead_id"
            )

            total_leads = len(companies)
            leads_com_website = sum(1 for r in companies if r.get("tem_website"))
            leads_com_instagram = sum(1 for r in companies if r.get("tem_instagram"))
            leads_sem_presenca = sum(
                1 for r in companies
                if not r.get("tem_website") and not r.get("tem_facebook") and not r.get("tem_instagram")
            )
            leads_no_crm = sum(1 for r in companies if r.get("crm_lead_id") is not None)
            leads_disponiveis = sum(1 for r in companies if r.get("crm_lead_id") is None)
            scores = [
                float(r["score_oportunidade_comercial"])
                for r in companies
                if r.get("score_oportunidade_comercial") is not None
            ]
            media_score = round(sum(scores) / len(scores), 2) if scores else 0.0

            # Active jobs
            jobs = sb_select("prospect_jobs", filters={"status": "eq.a_correr"}, select="id")
            jobs_ativos = len(jobs)

            stats = {
                "total_leads": total_leads,
                "leads_com_website": leads_com_website,
                "leads_com_instagram": leads_com_instagram,
                "leads_sem_presenca_digital": leads_sem_presenca,
                "leads_no_crm": leads_no_crm,
                "leads_disponiveis": leads_disponiveis,
                "jobs_ativos": jobs_ativos,
                "media_score_oportunidade": media_score,
            }

            status, headers, body = json_response(stats)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
