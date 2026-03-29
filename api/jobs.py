"""
GET  /api/jobs — list all jobs
POST /api/jobs — create a new scraping job (runs inline, serverless)
"""
from http.server import BaseHTTPRequestHandler
import sys
import os
import json
import uuid
import threading
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))

from lib.db import execute_query, execute_write
from lib.helpers import json_response, error_response, send_response, parse_body
from lib.scraper import scrape_paginas_amarelas, check_digital_presence, calculate_scores


def run_scraping_job(job_id: str, nicho: str, localidade: str, max_results: int):
    """
    Run scraping job in background thread.
    Updates job status and inserts companies into DB.
    """
    try:
        # Update status to running
        execute_write(
            "UPDATE jobs SET status = 'a_correr', progresso = 0 WHERE id = %s",
            (job_id,),
        )

        # Scrape
        raw_companies = scrape_paginas_amarelas(nicho, localidade, max_results)
        total = len(raw_companies)

        inserted = 0
        for i, company in enumerate(raw_companies):
            try:
                # Check digital presence
                presence = check_digital_presence(company.get("website"))

                # Merge data
                full_data = {
                    **company,
                    **presence,
                    "nicho": company.get("nicho", nicho),
                    "localidade": company.get("localidade", localidade),
                    "status": "novo",
                    "fonte": "Páginas Amarelas",
                }

                # Social from website scraping
                full_data.setdefault("tem_facebook", False)
                full_data.setdefault("tem_instagram", False)
                full_data.setdefault("tem_linkedin", False)
                full_data.setdefault("tem_youtube", False)
                full_data.setdefault("tem_tiktok", False)

                scores = calculate_scores(full_data)
                full_data.update(scores)

                # Insert (ignore duplicates by nome+localidade)
                execute_write(
                    """
                    INSERT INTO companies (
                        id, nome, nicho, localidade, morada, telefone, email, website,
                        tem_website, tem_loja_online, tem_facebook, tem_instagram,
                        tem_linkedin, tem_youtube, tem_tiktok,
                        tem_google_ads, tem_facebook_ads, tem_gtm, tem_ga4, tem_pixel_meta,
                        score_maturidade_digital, score_oportunidade_comercial, score_prioridade_sdr,
                        status, fonte
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (nome, localidade) DO NOTHING
                    """,
                    (
                        str(uuid.uuid4()),
                        full_data.get("nome", "")[:255],
                        full_data.get("nicho", "")[:100],
                        full_data.get("localidade", "")[:100],
                        full_data.get("morada", "")[:255],
                        full_data.get("telefone", "")[:50],
                        full_data.get("email", "")[:255],
                        full_data.get("website", "")[:255],
                        bool(full_data.get("tem_website")),
                        bool(full_data.get("tem_loja_online")),
                        bool(full_data.get("tem_facebook")),
                        bool(full_data.get("tem_instagram")),
                        bool(full_data.get("tem_linkedin")),
                        bool(full_data.get("tem_youtube")),
                        bool(full_data.get("tem_tiktok")),
                        bool(full_data.get("tem_google_ads")),
                        bool(full_data.get("tem_facebook_ads")),
                        bool(full_data.get("tem_gtm")),
                        bool(full_data.get("tem_ga4")),
                        bool(full_data.get("tem_pixel_meta")),
                        full_data.get("score_maturidade_digital"),
                        full_data.get("score_oportunidade_comercial"),
                        full_data.get("score_prioridade_sdr"),
                        "novo",
                        "Páginas Amarelas",
                    ),
                )
                inserted += 1
            except Exception:
                pass

            # Update progress
            progress = int(((i + 1) / max(total, 1)) * 100)
            execute_write(
                "UPDATE jobs SET progresso = %s, total_encontrados = %s WHERE id = %s",
                (progress, inserted, job_id),
            )

        # Mark complete
        execute_write(
            """
            UPDATE jobs SET
                status = 'concluido',
                progresso = 100,
                total_encontrados = %s,
                data_fim = NOW()
            WHERE id = %s
            """,
            (inserted, job_id),
        )

    except Exception as e:
        execute_write(
            """
            UPDATE jobs SET
                status = 'erro',
                mensagem_erro = %s,
                data_fim = NOW()
            WHERE id = %s
            """,
            (str(e)[:500], job_id),
        )


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _, headers, _ = json_response({})
        send_response(self, 200, headers, "")

    def do_GET(self):
        try:
            jobs = execute_query(
                "SELECT * FROM jobs ORDER BY data_inicio DESC LIMIT 100"
            )
            status, headers, body = json_response(jobs)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)
        send_response(self, status, headers, body)

    def do_POST(self):
        try:
            data = parse_body(self)
            nicho = data.get("nicho", "").strip()
            localidade = data.get("localidade", "").strip()
            max_resultados = min(int(data.get("max_resultados", 50)), 200)

            if not nicho or not localidade:
                status, headers, body = error_response(
                    "nicho e localidade são obrigatórios"
                )
                send_response(self, status, headers, body)
                return

            job_id = str(uuid.uuid4())

            # Create job record
            job = execute_write(
                """
                INSERT INTO jobs (id, nicho, localidade, max_resultados, status, progresso, total_encontrados)
                VALUES (%s, %s, %s, %s, 'pendente', 0, 0)
                RETURNING *
                """,
                (job_id, nicho, localidade, max_resultados),
            )

            # Run in background thread
            # Note: Vercel serverless functions run the thread until the response
            # is sent. For long jobs, consider using Vercel Cron + QStash instead.
            t = threading.Thread(
                target=run_scraping_job,
                args=(job_id, nicho, localidade, max_resultados),
                daemon=True,
            )
            t.start()

            status, headers, body = json_response(job, 201)
        except Exception as e:
            status, headers, body = error_response(str(e), 500)

        send_response(self, status, headers, body)
