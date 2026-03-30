"""
Supabase REST API client.
Replaces psycopg2 — uses only urllib (stdlib, no external deps).
Env vars required: SUPABASE_URL, SUPABASE_KEY (service_role key)
"""
import os
import json
import urllib.request
import urllib.parse
import urllib.error

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


def _base_headers(extra=None):
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


def _rest_url(table, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params:
        # build query string, keeping duplicate keys (PostgREST needs them)
        parts = []
        for k, v in params.items():
            if isinstance(v, list):
                for item in v:
                    parts.append(f"{urllib.parse.quote(str(k))}={urllib.parse.quote(str(item))}")
            else:
                parts.append(f"{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}")
        url += "?" + "&".join(parts)
    return url


def _do_request(req):
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read()
            content_range = resp.headers.get("content-range", "")
            data = json.loads(body) if body else []
            return data, content_range
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise Exception(f"Supabase {e.code}: {err_body}")


# ─── SELECT ────────────────────────────────────────────────────────────────────

def sb_select(table, filters=None, select="*", order=None, limit=None, offset=None):
    """Fetch rows. Returns list of dicts."""
    params = {"select": select}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order
    if limit is not None:
        params["limit"] = str(limit)
    if offset is not None:
        params["offset"] = str(offset)
    req = urllib.request.Request(_rest_url(table, params), headers=_base_headers())
    data, _ = _do_request(req)
    return data if isinstance(data, list) else [data]


def sb_select_count(table, filters=None, select="*", order=None, limit=None, offset=None):
    """Fetch rows + total count (uses Prefer: count=exact)."""
    params = {"select": select}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order
    if limit is not None:
        params["limit"] = str(limit)
    if offset is not None:
        params["offset"] = str(offset)
    hdrs = _base_headers({"Prefer": "count=exact"})
    req = urllib.request.Request(_rest_url(table, params), headers=hdrs)
    data, content_range = _do_request(req)
    # content-range: 0-19/142  or  */0
    total = 0
    if "/" in content_range:
        try:
            total = int(content_range.split("/")[-1])
        except ValueError:
            total = len(data) if isinstance(data, list) else 0
    rows = data if isinstance(data, list) else []
    return rows, total


def sb_select_one(table, filters=None, select="*"):
    """Fetch single row or None."""
    rows = sb_select(table, filters=filters, select=select, limit=1)
    return rows[0] if rows else None


# ─── INSERT ────────────────────────────────────────────────────────────────────

def sb_insert(table, data, on_conflict=None, ignore_duplicates=False):
    """INSERT row(s). Returns inserted row or None."""
    params = {}
    if on_conflict:
        params["on_conflict"] = on_conflict
    prefer = "return=representation"
    if ignore_duplicates:
        prefer += ",resolution=ignore-duplicates"
    hdrs = _base_headers({"Prefer": prefer})
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        _rest_url(table, params if params else None),
        data=body, headers=hdrs, method="POST"
    )
    result, _ = _do_request(req)
    if isinstance(result, list):
        return result[0] if result else None
    return result


# ─── UPDATE ────────────────────────────────────────────────────────────────────

def sb_update(table, match_filters, data):
    """UPDATE rows matching filters. Returns updated row or None."""
    hdrs = _base_headers({"Prefer": "return=representation"})
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        _rest_url(table, match_filters),
        data=body, headers=hdrs, method="PATCH"
    )
    result, _ = _do_request(req)
    if isinstance(result, list):
        return result[0] if result else None
    return result


# ─── DELETE ────────────────────────────────────────────────────────────────────

def sb_delete(table, match_filters):
    """DELETE rows matching filters."""
    hdrs = _base_headers({"Prefer": "return=representation"})
    req = urllib.request.Request(
        _rest_url(table, match_filters),
        headers=hdrs, method="DELETE"
    )
    result, _ = _do_request(req)
    return result
