"""GET /api/leads — list leads with filters & pagination.

CHANGELOG:
- Novo filtro: classificacao (excelente / bom / fraco)
- Novo filtro: sem_email=1
- Novo filtro: sem_telefone=1
- Ordenação padrão alterada para score_qualidade_lead
"""
from http.server import BaseHTTPRequestHandler
import sys
import os
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))

from lib.db import sb_select_count
from lib.helpers import json_response, error_response, send_response


def build_filters(params):
    """Convert query params into PostgREST filter dict."""
    filters = {}

    if params.get("status"):
        filters["status"] = f"eq.{params['status']}"

    # NOVO: filtro por classificação do lead
    if params.get("classificacao"):
        filters["classificacao_lead"] = f"eq.{params['classificacao']}"

    if params.get("nicho"):
        filters["nicho"] = f"ilike.*{params['nicho']}*"

    if params.get("localidade"):
        filters["localidade"] = f"ilike.*{params['localidade']}*"

    if params.get("search"):
        q = params["search"]
        filters["or"] = f"(nome.ilike.*{q}*,localidade.ilike.*{q}*,nicho.ilike.*{q}*)"

    # NOVO: leads sem email
    if params.get("sem_email") == "1":
        filters["email"] = "is.null"

    # NOVO: leads sem telefone
    if params.get("sem_telefone") == "1":
        filters["telefone"] = "is.null"

    return filters


def build_order(params):
    allowed = {
        "score_qualidade_lead",           # NOVO padrão
        "score_prioridade_sdr",
        "score_oportunidade_comercial",
        "score_maturidade_digital",
        "data_criacao",
        "nome",
    }
    sort_by = params.get("sort_by", "score_qualidade_lead")
    if sort_by not in allowed:
        sort_by = "score_qualidade_lead"
    direction = "asc" if params.get("sort_dir") == "asc" else "desc"
    return f"{sort_by}.{direction}.nullslast"


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        try:
            per_page = min(int(params.get("per_page", 20)), 100)
            page     = max(1, int(params.get("page", 1)))
            offset   = (page - 1) * per_page

            filters = build_filters(params)
            order   = build_order(params)

            leads, total = sb_select_count(
                "companies",
                filters=filters,
                order=order,
                limit=per_page,
                offset=offset,
            )

            status, headers, body = json_response({
                "leads":    leads,
                "total":    total,
                "page":     page,
                "per_page": per_page,
            })
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
