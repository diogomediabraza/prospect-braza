"""POST /api/jobs/[id]/cancel — cancel a running or pending job."""
from http.server import BaseHTTPRequestHandler
import sys
import os
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from lib.db import execute_write, execute_one
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
        # path: /api/jobs/{id}/cancel
        job_id = parts[2] if len(parts) > 2 else None

        if not job_id:
            status, headers, body = error_response("Job ID em falta")
            send_response(self, status, headers, body)
            return

        try:
            job = execute_one("SELECT * FROM jobs WHERE id = %s", (job_id,))
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

            updated = execute_write(
                """
                UPDATE jobs
                SET status = 'cancelado', data_fim = NOW()
                WHERE id = %s
                RETURNING *
                """,
                (job_id,),
            )
            status, headers, body = json_response(updated)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
