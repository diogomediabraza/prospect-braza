"""
GET  /api/leads  — list leads with filters & pagination
PATCH /api/leads/[id] — update status/notes (handled by leads/[id].py)
"""
from http.server import BaseHTTPRequestHandler
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.db import execute_query, execute_one
from lib.helpers import json_response, error_response, send_response
import json
import urllib.parse


def build_leads_query(params: dict) -> tuple[str, list]:
    """Build SQL query from filter params."""
    conditions = []
    values = []

    if params.get("status"):
        conditions.append("status = %s")
        values.append(params["status"])

    if params.get("nicho"):
        conditions.append("nicho ILIKE %s")
        values.append(f"%{params['nicho']}%")

    if params.get("localidade"):
        conditions.append("localidade ILIKE %s")
        values.append(f"%{params['localidade']}%")

    if params.get("search"):
        conditions.append(
            "(nome ILIKE %s OR localidade ILIKE %s OR nicho ILIKE %s)"
        )
        q = f"%{params['search']}%"
        values.extend([q, q, q])

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Sorting
    allowed_sorts = {
        "score_prioridade_sdr",
        "score_oportunidade_comercial",
        "score_maturidade_digital",
        "data_criacao",
        "nome",
    }
    sort_by = params.get("sort_by", "score_prioridade_sdr")
    if sort_by not in allowed_sorts:
        sort_by = "score_prioridade_sdr"
    sort_dir = "ASC" if params.get("sort_dir") == "asc" else "DESC"

    # Pagination
    per_page = min(int(params.get("per_page", 20)), 100)
    page = max(1, int(params.get("page", 1)))
    offset = (page - 1) * per_page

    count_query = f"SELECT COUNT(*) as total FROM companies {where}"
    data_query = f"""
        SELECT * FROM companies
        {where}
        ORDER BY {sort_by} {sort_dir} NULLS LAST
        LIMIT %s OFFSET %s
    """
    values_data = values + [per_page, offset]

    return count_query, values, data_query, values_data, page, per_page


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default logging

    def do_OPTIONS(self):
        status, headers, body = json_response({})
        send_response(self, 200, headers, "")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        try:
            count_q, count_v, data_q, data_v, page, per_page = build_leads_query(params)

            # Get total
            count_row = execute_one(count_q, count_v)
            total = count_row["total"] if count_row else 0

            # Get leads
            leads = execute_query(data_q, data_v)

            status, headers, body = json_response({
                "leads": leads,
                "total": total,
                "page": page,
                "per_page": per_page,
            })
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
