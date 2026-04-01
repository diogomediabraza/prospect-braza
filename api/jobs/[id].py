"""GET /DELETE /api/jobs/[id] — get or delete a single job."""
from http.server import BaseHTTPRequestHandler
import sys
import os
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lib.db import sb_select_one, sb_delete
from lib.helpers import json_response, error_response, send_response


def _get_job_id(path):
    parsed = urllib.parse.urlparse(path)
    params = dict(urllib.parse.parse_qsl(parsed.query))
    return params.get("id") or path.rstrip("/").split("/")[-1]


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def do_GET(self):
        job_id = _get_job_id(self.path)
        try:
            job = sb_select_one("jobs", filters={"id": f"eq.{job_id}"})
            if not job:
                status, headers, body = error_response("Job não encontrado", 404)
            else:
                status, headers, body = json_response(job)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)
        send_response(self, status, headers, body)

    def do_DELETE(self):
        job_id = _get_job_id(self.path)
        try:
            job = sb_select_one("jobs", filters={"id": f"eq.{job_id}"})
            if not job:
                status, headers, body = error_response("Job não encontrado", 404)
            else:
                sb_delete("companies", {"job_id": f"eq.{job_id}"})
                sb_delete("jobs", {"id": f"eq.{job_id}"})
                status, headers, body = json_response({"deleted": True, "id": job_id})
        except Exception as e:
            status, headers, body = error_response(str(e), 500)
        send_response(self, status, headers, body)
