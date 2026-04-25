"""POST /api/leads/to-crm — push a prospect lead into the CRM.

Creates a crm_leads row from a prospect_companies row and
links them via crm_lead_id.
"""
from http.server import BaseHTTPRequestHandler
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lib.db import sb_select_one, sb_insert, sb_update
from lib.helpers import json_response, error_response, send_response, parse_body


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def do_POST(self):
        try:
            data = parse_body(self)
            lead_id = data.get("lead_id")

            if not lead_id:
                status, headers, body = error_response("lead_id é obrigatório")
                send_response(self, status, headers, body)
                return

            # Fetch the prospect lead
            lead = sb_select_one("prospect_companies", filters={"id": f"eq.{lead_id}"})
            if not lead:
                status, headers, body = error_response("Lead não encontrado", 404)
                send_response(self, status, headers, body)
                return

            # Check if already in CRM
            if lead.get("crm_lead_id"):
                status, headers, body = json_response({
                    "ok": False,
                    "msg": "Este lead já está no CRM",
                    "crm_lead_id": lead["crm_lead_id"],
                })
                send_response(self, status, headers, body)
                return

            # Build CRM lead from prospect data
            instagram_handle = lead.get("instagram") or ""
            if instagram_handle and "instagram.com/" in instagram_handle:
                instagram_handle = "@" + instagram_handle.split("instagram.com/")[-1].strip("/")
            elif instagram_handle and not instagram_handle.startswith("@"):
                instagram_handle = "@" + instagram_handle

            # Build notes with extra prospect data
            notes_parts = []
            if lead.get("nicho"):
                notes_parts.append(f"Nicho: {lead['nicho']}")
            if lead.get("localidade"):
                notes_parts.append(f"Localidade: {lead['localidade']}")
            if lead.get("morada"):
                notes_parts.append(f"Morada: {lead['morada']}")
            if lead.get("email"):
                notes_parts.append(f"Email: {lead['email']}")
            if lead.get("telefone2"):
                notes_parts.append(f"Telefone 2: {lead['telefone2']}")
            if lead.get("facebook"):
                notes_parts.append(f"Facebook: {lead['facebook']}")
            if lead.get("linkedin"):
                notes_parts.append(f"LinkedIn: {lead['linkedin']}")
            if lead.get("score_qualidade_lead") is not None:
                notes_parts.append(f"Score Qualidade: {lead['score_qualidade_lead']}/100")
            if lead.get("classificacao_lead"):
                notes_parts.append(f"Classificação: {lead['classificacao_lead']}")
            notes_parts.append("Origem: Prospect Braza")

            crm_row = {
                "title": lead["nome"],
                "phone": lead.get("telefone") or None,
                "instagram": instagram_handle or None,
                "website": lead.get("website") or None,
                "source": "cold_outreach",
                "temperature": "cold",
                "status": "new",
                "notes": " | ".join(notes_parts),
                "tags": [lead.get("nicho", "prospect"), "prospect-braza"],
            }

            # Optional: assign owner from claimed_by or request header
            owner = data.get("owner_id")
            if owner:
                crm_row["owner_id"] = owner

            # Insert into CRM
            crm_lead = sb_insert("crm_leads", crm_row)

            if crm_lead and crm_lead.get("id"):
                # Link back to prospect
                sb_update(
                    "prospect_companies",
                    {"id": f"eq.{lead_id}"},
                    {"crm_lead_id": crm_lead["id"], "status": "abordado"},
                )

                status, headers, body = json_response({
                    "ok": True,
                    "crm_lead_id": crm_lead["id"],
                    "msg": f"Lead '{lead['nome']}' inserido no CRM com sucesso",
                }, 201)
            else:
                status, headers, body = error_response("Falha ao inserir no CRM", 500)

        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
