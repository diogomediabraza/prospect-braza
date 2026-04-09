"""GET /api/purge — apaga todos os leads da base (limpeza manual)."""
from http.server import BaseHTTPRequestHandler
import sys
import os
import json
import urllib.request
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from lib.helpers import json_response, send_response


def _sb_delete_all(table: str):
    url_base = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if not url_base or not key:
        raise RuntimeError("Supabase env vars not set")
    # Use id gt null-uuid to match all records
    params = urllib.parse.urlencode({"id": "gt.00000000-0000-0000-0000-000000000000"})
    url = f"{url_base}/rest/v1/{table}?{params}"
    req = urllib.request.Request(
        url,
        method="DELETE",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


class handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def do_GET(self):
        try:
            _sb_delete_all("prospect_companies")
            status, headers, body = json_response({"ok": True, "msg": "Todos os leads apagados com sucesso."})
        except Exception as e:
            status, headers, body = json_response({"ok": False, "error": str(e)}, 500)
        send_response(self, status, headers, body)
