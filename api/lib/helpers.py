"""Shared helpers for serverless API functions."""
import json
from http.server import BaseHTTPRequestHandler
from typing import Any


def json_response(data: Any, status: int = 200) -> tuple[int, dict, str]:
    """Build a JSON response tuple."""
    body = json.dumps(data, ensure_ascii=False, default=str)
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
    return status, headers, body


def error_response(message: str, status: int = 400) -> tuple[int, dict, str]:
    return json_response({"detail": message}, status)


def parse_body(handler: BaseHTTPRequestHandler) -> dict:
    """Parse JSON body from request."""
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def send_response(handler: BaseHTTPRequestHandler, status: int, headers: dict, body: str):
    handler.send_response(status)
    for k, v in headers.items():
        handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(body.encode("utf-8"))
