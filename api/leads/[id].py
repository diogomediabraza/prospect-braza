"""
GET    /api/leads/[id] — get single lead
PATCH  /api/leads/[id] — update status/notes/claim/crm
DELETE /api/leads/[id] — delete lead
"""
from http.server import BaseHTTPRequestHandler
import sys
import os
import urllib.parse
from datetime import datetime, timezone

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
            lead = sb_select_one("prospect_companies", filters={"id": f"eq.{lead_id}"})
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

            # Expanded allowed fields — now includes claimed_by, claimed_at, crm_lead_id
            allowed = {"status", "notas", "claimed_by", "claimed_at", "crm_lead_id"}
            updates = {k: v for k, v in data.items() if k in allowed}

            # Auto-set claimed_at when claimed_by is provided
            if "claimed_by" in updates and updates["claimed_by"]:
                if "claimed_at" not in updates:
                    updates["claimed_at"] = datetime.now(timezone.utc).isoformat()

            # Auto-set claimed_by when status changes from 'novo' to something else
            if "status" in updates and updates["status"] != "novo":
                if "claimed_by" not in updates:
                    current = sb_select_one("prospect_companies", {"id": f"eq.{lead_id}"}, select="status,claimed_by")
                    if current and current.get("status") == "novo" and not current.get("claimed_by"):
                        user = self.headers.get("X-User-Name") or self.headers.get("X-User-Email")
                        if user:
                            updates["claimed_by"] = user
                            updates["claimed_at"] = datetime.now(timezone.utc).isoformat()

            if not updates:
                status, headers, body = error_response("Nenhum campo válido para actualizar")
                send_response(self, status, headers, body)
                return

            updated = sb_update("prospect_companies", {"id": f"eq.{lead_id}"}, updates)
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
            sb_delete("prospect_companies", {"id": f"eq.{lead_id}"})
            status, headers, body = json_response({"ok": True})
        except Exception as e:
            status, headers, body = error_response(str(e), 500)
        send_response(self, status, headers, body)
