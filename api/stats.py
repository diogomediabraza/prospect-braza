"""GET /api/stats — dashboard statistics."""
from http.server import BaseHTTPRequestHandler
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.db import execute_one
from lib.helpers import json_response, error_response, send_response


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def do_GET(self):
        try:
            row = execute_one(
                """
                SELECT
                    COUNT(*)                                          AS total_leads,
                    COUNT(*) FILTER (WHERE tem_website = true)        AS leads_com_website,
                    COUNT(*) FILTER (WHERE tem_instagram = true)      AS leads_com_instagram,
                    COUNT(*) FILTER (
                        WHERE tem_website = false
                        AND tem_facebook = false
                        AND tem_instagram = false
                    )                                                  AS leads_sem_presenca_digital,
                    AVG(score_oportunidade_comercial)                  AS media_score_oportunidade
                FROM companies
                """,
            )

            jobs_row = execute_one(
                "SELECT COUNT(*) AS jobs_ativos FROM jobs WHERE status = 'a_correr'"
            )

            stats = {
                "total_leads": int(row.get("total_leads") or 0),
                "leads_com_website": int(row.get("leads_com_website") or 0),
                "leads_com_instagram": int(row.get("leads_com_instagram") or 0),
                "leads_sem_presenca_digital": int(row.get("leads_sem_presenca_digital") or 0),
                "jobs_ativos": int(jobs_row.get("jobs_ativos") or 0),
                "media_score_oportunidade": float(row.get("media_score_oportunidade") or 0),
            }

            status, headers, body = json_response(stats)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
