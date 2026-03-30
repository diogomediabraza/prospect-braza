"""POST /api/jobs/[id]/cancel — cancel a running or pending job."""
from http.server import BaseHTTPRequestHandler
import sys
import os
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from lib.db import sb_select_one, sb_update
from lib.helpers import json_response, error_response, send_response


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        job_id = parts[2] if len(parts) > 2 else None

        if not job_id:
            status, headers, body = error_response("Job ID em falta")
            send_response(self, status, headers, body)
            return

        try:
            job = sb_select_one("jobs", filters={"id": f"eq.{job_id}"})
            if not job:
                status, headers, body = error_response("Job não encontrado", 404)
                send_response(self, status, headers, body)
                return

            if job["status"] not in ("pendente", "a_correr"):
                status, headers, body = error_response(
                    "Só é possível cancelar jobs pendentes ou em curso"
                )
                send_response(self, status, headers, body)
                return

            updated = sb_update(
                "jobs", {"id": f"eq.{job_id}"},
                {"status": "cancelado", "data_fim": "now()"}
            )
            status, headers, body = json_response(updated)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
