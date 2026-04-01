"""GET /api/leads/export — export leads as CSV.

CHANGELOG:
- Novos campos no CSV: classificacao_lead, score_qualidade_lead,
  confianca_email, confianca_telefone, fontes_encontradas
- Novo filtro: classificacao
- Ordenação padrão por score_qualidade_lead DESC
"""
from http.server import BaseHTTPRequestHandler
import sys
import os
import csv
import io
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lib.db import sb_select
from lib.helpers import error_response, send_response


CSV_COLUMNS = [
    ("nome",                        "Nome"),
    ("nicho",                       "Nicho"),
    ("localidade",                  "Localidade"),
    ("morada",                      "Morada"),
    ("telefone",                    "Telefone"),
    ("telefone2",                   "Telefone 2"),
    ("email",                       "Email"),
    ("website",                     "Website"),
    ("facebook",                    "Facebook"),
    ("instagram",                   "Instagram"),
    ("linkedin",                    "LinkedIn"),
    ("youtube",                     "YouTube"),
    ("classificacao_lead",          "Classificação Lead"),      # NOVO
    ("score_qualidade_lead",        "Score Qualidade (0-100)"), # NOVO
    ("confianca_email",             "Confiança Email"),         # NOVO
    ("confianca_telefone",          "Confiança Telefone"),      # NOVO
    ("tem_website",                 "Tem Website"),
    ("tem_instagram",               "Tem Instagram"),
    ("tem_facebook",                "Tem Facebook"),
    ("tem_google_ads",              "Tem Google Ads"),
    ("tem_facebook_ads",            "Tem Meta Ads"),
    ("tem_gtm",                     "Tem GTM"),
    ("tem_ga4",                     "Tem GA4"),
    ("tem_pixel_meta",              "Tem Pixel Meta"),
    ("score_maturidade_digital",    "Score Maturidade Digital"),
    ("score_oportunidade_comercial","Score Oportunidade"),
    ("score_prioridade_sdr",        "Score Prioridade SDR"),
    ("status",                      "Status CRM"),
    ("notas",                       "Notas"),
    ("fonte",                       "Fonte Principal"),
    ("fontes_encontradas",          "Todas as Fontes"),         # NOVO
    ("ultima_validacao",            "Última Validação"),        # NOVO
    ("data_criacao",                "Data Criação"),
]


class handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        try:
            filters = {}
            if params.get("status"):
                filters["status"] = f"eq.{params['status']}"
            if params.get("classificacao"):
                filters["classificacao_lead"] = f"eq.{params['classificacao']}"
            if params.get("nicho"):
                filters["nicho"] = f"ilike.*{params['nicho']}*"
            if params.get("localidade"):
                filters["localidade"] = f"ilike.*{params['localidade']}*"

            # Por defeito exporta apenas leads válidos (exclui lixo)
            # Se não houver filtro de classificação, excluir automaticamente o lixo
            if not filters.get("classificacao_lead"):
                filters["classificacao_lead"] = "neq.lixo"

            rows = sb_select(
                "companies",
                filters=filters if filters else None,
                order="score_qualidade_lead.desc.nullslast",
                limit=5000,
            )

            output = io.StringIO()
            writer = csv.writer(output, delimiter=";")
            writer.writerow([col[1] for col in CSV_COLUMNS])
            for row in rows:
                csv_row = []
                for col, _ in CSV_COLUMNS:
                    val = row.get(col, "")
                    # Serializar arrays (fontes_encontradas) como string
                    if isinstance(val, list):
                        val = ", ".join(str(v) for v in val)
                    csv_row.append(val)
                writer.writerow(csv_row)

            csv_bytes = ("\ufeff" + output.getvalue()).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="prospect-braza.csv"')
            self.send_header("Content-Length", str(len(csv_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(csv_bytes)

        except Exception as e:
            status, headers, body = error_response(str(e), 500)
            send_response(self, status, headers, body)
