"""GET /api/jobs/[id] — get single job."""
from http.server import BaseHTTPRequestHandler
import sys
import os
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lib.db import sb_select_one
from lib.helpers import json_response, error_response, send_response


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        job_id = params.get("id") or self.path.rstrip("/").split("/")[-1]

        try:
            job = sb_select_one("jobs", filters={"id": f"eq.{job_id}"})
            if not job:
                status, headers, body = error_response("Job não encontrado", 404)
            else:
                status, headers, body = json_response(job)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
