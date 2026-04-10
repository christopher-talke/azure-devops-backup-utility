"""ADO Backup Dashboard - Azure Functions v2 HTTP endpoints.

All endpoints are read-only and only access _indexes/ metadata blobs.
Raw backup data is not served; admins go to the storage container directly.
"""

import json
import os
from pathlib import Path
from urllib.parse import unquote

import azure.functions as func

from . import discover_backups, download_blob_json, download_blob_text

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.route(route="api/backups", methods=["GET"])
def list_backups(req: func.HttpRequest) -> func.HttpResponse:
    """Return a JSON array of all backup runs."""
    limit = int(req.params.get("limit", "50"))
    offset = int(req.params.get("offset", "0"))

    backups = discover_backups()
    page = backups[offset : offset + limit]

    return func.HttpResponse(
        json.dumps({"backups": page, "total": len(backups)}, indent=2),
        mimetype="application/json",
    )


@app.route(route="api/backups/{backup_id}/manifest", methods=["GET"])
def get_manifest(req: func.HttpRequest) -> func.HttpResponse:
    """Return the full manifest.json for a backup run."""
    backup_id = unquote(req.route_params["backup_id"])
    blob_path = f"{backup_id}/_indexes/manifest.json"
    data = download_blob_json(blob_path)
    if data is None:
        return func.HttpResponse("Backup not found", status_code=404)
    return func.HttpResponse(json.dumps(data, indent=2), mimetype="application/json")


@app.route(route="api/backups/{backup_id}/errors", methods=["GET"])
def get_errors(req: func.HttpRequest) -> func.HttpResponse:
    """Return errors.jsonl parsed as a JSON array."""
    backup_id = unquote(req.route_params["backup_id"])
    blob_path = f"{backup_id}/_indexes/errors.jsonl"
    text = download_blob_text(blob_path)
    if text is None:
        return func.HttpResponse(
            json.dumps([]), mimetype="application/json"
        )

    limit = int(req.params.get("limit", "500"))
    errors = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            errors.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(errors) >= limit:
            break

    return func.HttpResponse(json.dumps(errors, indent=2), mimetype="application/json")


@app.route(route="api/backups/{backup_id}/inventory", methods=["GET"])
def get_inventory(req: func.HttpRequest) -> func.HttpResponse:
    """Return inventory.json with optional category filter."""
    backup_id = unquote(req.route_params["backup_id"])
    blob_path = f"{backup_id}/_indexes/inventory.json"
    data = download_blob_json(blob_path)
    if data is None:
        return func.HttpResponse(
            json.dumps([]), mimetype="application/json"
        )

    category_filter = req.params.get("category")
    if category_filter and isinstance(data, list):
        data = [e for e in data if e.get("category") == category_filter]

    return func.HttpResponse(json.dumps(data, indent=2), mimetype="application/json")


@app.route(route="api/backups/{backup_id}/verification", methods=["GET"])
def get_verification(req: func.HttpRequest) -> func.HttpResponse:
    """Return verification_report.json (404 if backup ran without --verify)."""
    backup_id = unquote(req.route_params["backup_id"])
    blob_path = f"{backup_id}/_indexes/verification_report.json"
    data = download_blob_json(blob_path)
    if data is None:
        return func.HttpResponse("No verification report", status_code=404)
    return func.HttpResponse(json.dumps(data, indent=2), mimetype="application/json")


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------

_MIME_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
}


def _serve_static(filename: str) -> func.HttpResponse:
    """Serve a file from the frontend/ directory."""
    filepath = _FRONTEND_DIR / filename
    if not filepath.is_file():
        return func.HttpResponse("Not found", status_code=404)
    content = filepath.read_text(encoding="utf-8")
    mime = _MIME_TYPES.get(filepath.suffix, "text/plain")
    return func.HttpResponse(content, mimetype=mime)


@app.route(route="", methods=["GET"])
def index(req: func.HttpRequest) -> func.HttpResponse:
    return _serve_static("index.html")


@app.route(route="index.html", methods=["GET"])
def index_html(req: func.HttpRequest) -> func.HttpResponse:
    return _serve_static("index.html")


@app.route(route="style.css", methods=["GET"])
def style_css(req: func.HttpRequest) -> func.HttpResponse:
    return _serve_static("style.css")


@app.route(route="app.js", methods=["GET"])
def app_js(req: func.HttpRequest) -> func.HttpResponse:
    return _serve_static("app.js")
