"""
GET    /api/leads/[id] — get single lead
PATCH  /api/leads/[id] — update status/notes
DELETE /api/leads/[id] — delete lead
"""
from http.server import BaseHTTPRequestHandler
import sys
import os
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lib.db import sb_select_one, sb_update, sb_delete
from lib.helpers import json_response, error_response, send_response, parse_body


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def _get_id(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        return params.get("id") or self.path.rstrip("/").split("/")[-1]

    def do_GET(self):
        lead_id = self._get_id()
        try:
            lead = sb_select_one("companies", filters={"id": f"eq.{lead_id}"})
            if not lead:
                status, headers, body = error_response("Lead não encontrado", 404)
            else:
                status, headers, body = json_response(lead)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)
        send_response(self, status, headers, body)

    def do_PATCH(self):
        lead_id = self._get_id()
        try:
            data = parse_body(self)
            allowed = {"status", "notas"}
            updates = {k: v for k, v in data.items() if k in allowed}

            if not updates:
                status, headers, body = error_response("Nenhum campo válido para actualizar")
                send_response(self, status, headers, body)
                return

            updated = sb_update("companies", {"id": f"eq.{lead_id}"}, updates)
            if not updated:
                status, headers, body = error_response("Lead não encontrado", 404)
            else:
                status, headers, body = json_response(updated)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)
        send_response(self, status, headers, body)

    def do_DELETE(self):
        lead_id = self._get_id()
        try:
            sb_delete("companies", {"id": f"eq.{lead_id}"})
            status, headers, body = json_response({"ok": True})
        except Exception as e:
            status, headers, body = error_response(str(e), 500)
        send_response(self, status, headers, body)
