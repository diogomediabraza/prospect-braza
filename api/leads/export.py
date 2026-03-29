"""
GET /api/leads/export — export leads as CSV
"""
from http.server import BaseHTTPRequestHandler
import sys
import os
import csv
import io
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lib.db import execute_query
from lib.helpers import error_response, send_response


CSV_COLUMNS = [
    ("nome", "Nome"),
    ("nicho", "Nicho"),
    ("localidade", "Localidade"),
    ("morada", "Morada"),
    ("telefone", "Telefone"),
    ("telefone2", "Telefone 2"),
    ("email", "Email"),
    ("website", "Website"),
    ("facebook", "Facebook"),
    ("instagram", "Instagram"),
    ("linkedin", "LinkedIn"),
    ("youtube", "YouTube"),
    ("tem_website", "Tem Website"),
    ("tem_instagram", "Tem Instagram"),
    ("tem_facebook", "Tem Facebook"),
    ("tem_google_ads", "Tem Google Ads"),
    ("tem_facebook_ads", "Tem Meta Ads"),
    ("tem_gtm", "Tem GTM"),
    ("tem_ga4", "Tem GA4"),
    ("tem_pixel_meta", "Tem Pixel Meta"),
    ("score_maturidade_digital", "Score Maturidade Digital"),
    ("score_oportunidade_comercial", "Score Oportunidade"),
    ("score_prioridade_sdr", "Score Prioridade SDR"),
    ("status", "Status CRM"),
    ("notas", "Notas"),
    ("fonte", "Fonte"),
    ("data_criacao", "Data Criação"),
]


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        try:
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

            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            query = f"SELECT * FROM companies {where} ORDER BY score_prioridade_sdr DESC NULLS LAST LIMIT 5000"

            rows = execute_query(query, values if values else None)

            # Build CSV
            output = io.StringIO()
            writer = csv.writer(output, delimiter=";")

            # Header
            writer.writerow([col[1] for col in CSV_COLUMNS])

            # Rows
            for row in rows:
                writer.writerow([
                    row.get(col[0], "") for col in CSV_COLUMNS
                ])

            csv_content = output.getvalue()
            csv_bytes = ("\ufeff" + csv_content).encode("utf-8")  # BOM for Excel

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
