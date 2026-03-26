from flask import Blueprint, jsonify, request, abort
import requests
from ..database import db_connect, ensure_process_registered, link_doc_process
from ..utils.helpers import utcnow_iso, CNJ_REGEX, extract_list, normalize_doc, doc_type
from ..utils.logger import logger
from ..services.logic import (
    upsert_processo,
    _discover_link_for_doc,
    _get_watchlist_docs,
    _doc_has_links
)
from ..config import ESCAVADOR_TOKEN

api_v2_bp = Blueprint("api_v2", __name__)

def require_token():
    if not ESCAVADOR_TOKEN:
        abort(500, description="ESCAVADOR_TOKEN não configurado no ambiente/.env.")

@api_v2_bp.get("/health")
def health():
    return jsonify({"ok": True, "time": utcnow_iso()})

@api_v2_bp.get("/watchlist")
def list_watchlist():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT id, doc, tipo_doc, created_at FROM watchlist ORDER BY id DESC LIMIT 500")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"ok": True, "count": len(rows), "items": rows})

@api_v2_bp.post("/watchlist")
def create_watchlist():
    require_token()
    from ..app import client
    payload = request.get_json(force=True, silent=True) or {}
    doc_in = (payload.get("doc") or "").strip()
    if not doc_in: abort(400, description="Campo 'doc' é obrigatório.")
    try: doc = normalize_doc(doc_in)
    except ValueError as e: abort(400, description=str(e))
    tipo = doc_type(doc)

    api_resp = {}
    if client:
        try: api_resp = client.criar_monitor_novos_processos(doc)
        except Exception as e: api_resp = {"warning": str(e)}

    conn = db_connect(); cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO watchlist (doc, tipo_doc, created_at) VALUES (?, ?, ?)", (doc, tipo, utcnow_iso()))
    conn.commit()
    cur.execute("SELECT id FROM watchlist WHERE doc=?", (doc,)); row = cur.fetchone(); conn.close()
    return jsonify({"ok": True, "id": row["id"] if row else None, "doc": doc, "tipo_doc": tipo, "escavador": api_resp})

@api_v2_bp.delete("/watchlist/<int:watch_id>")
def delete_watchlist(watch_id: int):
    conn = db_connect(); cur = conn.cursor()
    cur.execute("DELETE FROM watchlist WHERE id=?", (watch_id,))
    conn.commit(); deleted = cur.rowcount; conn.close()
    return jsonify({"ok": True, "deleted": deleted})

@api_v2_bp.get("/processos/<path:cnj>/docs")
def list_docs_for_process(cnj: str):
    if not CNJ_REGEX.fullmatch(cnj): abort(400, description="CNJ inválido.")
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT doc, created_at FROM doc_process WHERE cnj=? ORDER BY created_at DESC", (cnj,))
    rows = [dict(r) for r in cur.fetchall()]; conn.close()
    return jsonify({"ok": True, "cnj": cnj, "count": len(rows), "items": rows})

@api_v2_bp.post("/docs/link")
def create_doc_link():
    payload = request.get_json(force=True, silent=True) or {}
    doc = (payload.get("doc") or "").strip()
    cnj = (payload.get("cnj") or "").strip()
    if not doc or not cnj: abort(400, description="Campos 'doc' e 'cnj' são obrigatórios.")
    try: docn = normalize_doc(doc)
    except Exception: abort(400, description="Doc inválido.")
    if not CNJ_REGEX.fullmatch(cnj): abort(400, description="CNJ inválido.")
    conn = db_connect()
    ensure_process_registered(conn, cnj)
    link_doc_process(conn, docn, cnj)
    conn.close()
    return jsonify({"ok": True, "doc": docn, "cnj": cnj})
