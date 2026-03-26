import json
import re
import sqlite3
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, abort, Response
from ..database import db_connect, ensure_process_registered
from ..utils.logger import logger
from ..utils.helpers import utcnow_iso, CNJ_REGEX, extract_list
from ..utils.state import get_poll_state, get_discover_state, get_last_api_error
from ..services.logic import sync_process_movements

api_ui_bp = Blueprint("api_ui", __name__, url_prefix="/ui/api")

@api_ui_bp.get("/alerts")
def get_alerts():
    limit = request.args.get("limit", 10, type=int)
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT cnj, data, tipo_inferido, texto FROM eventos_mov WHERE tipo_inferido IS NOT NULL ORDER BY data DESC, id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"ok": True, "items": rows})

@api_ui_bp.get("/dashboard/metrics")
def get_metrics():
    doc = request.args.get("doc")
    conn = db_connect()
    cur = conn.cursor()
    
    # Global/Per Doc Stats
    if doc:
        cur.execute("SELECT COUNT(*) FROM watchlist WHERE doc=?", (doc,))
        has_doc = cur.fetchone()[0] > 0
        if not has_doc: return jsonify({"ok": False, "error": "DOC_NOT_FOUND"}), 404
        
        cur.execute("SELECT COUNT(*) FROM doc_process WHERE doc=?", (doc,))
        total_processos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM eventos_mov e JOIN doc_process d ON e.cnj=d.cnj WHERE d.doc=?", (doc,))
        total_movs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM eventos_mov e JOIN doc_process d ON e.cnj=d.cnj WHERE d.doc=? AND e.tipo_inferido IS NOT NULL", (doc,))
        total_alerts = cur.fetchone()[0]
    else:
        cur.execute("SELECT COUNT(*) FROM watchlist")
        total_docs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM processos")
        total_processos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM eventos_mov")
        total_movs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM eventos_mov WHERE tipo_inferido IS NOT NULL")
        total_alerts = cur.fetchone()[0]

    # Costs
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    cur.execute("SELECT COALESCE(SUM(cost_brl),0) FROM api_usage WHERE substr(ts,1,10)=?", (today,))
    cost_today = float(cur.fetchone()[0])
    cur.execute("SELECT COALESCE(SUM(cost_brl),0) FROM api_usage WHERE substr(ts,1,7)=?", (month,))
    cost_month = float(cur.fetchone()[0])

    cur.execute("SELECT cnj, COUNT(*) as c FROM eventos_mov WHERE tipo_inferido IS NOT NULL " + ("AND cnj IN (SELECT cnj FROM doc_process WHERE doc=?)" if doc else "") + " GROUP BY cnj ORDER BY c DESC LIMIT 5", ([doc] if doc else []))
    top_cnjs = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT doc FROM watchlist ORDER BY doc ASC")
    docs_list = [r["doc"] for r in cur.fetchall()]
    
    metrics = {
        "ok": True,
        "docs": total_docs if not doc else 1,
        "processos": total_processos,
        "movs": total_movs,
        "alertas": total_alerts,
        "top_cnj_alerts": top_cnjs,
        "docs_list": docs_list,
        "poll_state": get_poll_state(),
        "discover_state": get_discover_state(),
        "last_api_error": get_last_api_error(),
        "cost_today_brl": cost_today,
        "cost_month_brl": cost_month
    }
    conn.close()
    return jsonify(metrics)

@api_ui_bp.get("/processo/<path:cnj>/documentos")
def get_documentos(cnj: str):
    if not CNJ_REGEX.fullmatch(cnj): abort(400)
    tipo = request.args.get("tipo", "publicos") # publicos | autos
    limit = 50
    page = 1
    
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT items_json, updated_at FROM docs_v2_cache WHERE cnj=? AND tipo=? AND limit_n=? AND page_n=?", (cnj, tipo, limit, page))
    row = cur.fetchone()
    if row:
        conn.close()
        return jsonify({"ok": True, "source": "cache", "items": json.loads(row["items_json"]), "updated_at": row["updated_at"]})
    
    from ..app import client
    if not client: abort(503)
    try:
        if tipo == "publicos": data = client.listar_documentos_publicos_v2(cnj, limit=limit, page=page)
        else: data = client.listar_autos_v2(cnj, limit=limit, page=page)
        
        items = extract_list(data)
        cur.execute("INSERT OR REPLACE INTO docs_v2_cache (cnj, tipo, limit_n, page_n, items_json, updated_at) VALUES (?,?,?,?,?,?)",
                    (cnj, tipo, limit, page, json.dumps(items, ensure_ascii=False), utcnow_iso()))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "source": "api", "items": items, "updated_at": utcnow_iso()})
    except Exception as e:
        conn.close()
        return jsonify({"ok": False, "error": str(e)})

@api_ui_bp.get("/processo/<path:cnj>/documentos/<path:key>/download")
def download_documento(cnj: str, key: str):
    from ..app import client
    if not client: abort(503)
    try:
        r = client.baixar_documento_pdf_v2(cnj, key)
        filename = f"{cnj}_{key}.pdf"
        return Response(r.content, headers={"Content-Type": "application/pdf", "Content-Disposition": f'attachment; filename="{filename}"'})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

@api_ui_bp.get("/processo/<path:cnj>/documentos/<path:key>/preview")
def preview_documento(cnj: str, key: str):
    from ..app import client
    if not client: abort(503)
    try:
        r = client.baixar_documento_pdf_v2(cnj, key)
        return Response(r.content, headers={"Content-Type": "application/pdf", "Content-Disposition": 'inline'})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

@api_ui_bp.post("/processo/<path:cnj>/solicitar-atualizacao")
def solicitar_atualizacao(cnj: str):
    from ..app import client
    if not client: abort(503)
    payload = request.get_json(silent=True) or {}
    tipo = payload.get("tipo", "autos") # autos | documentos_publicos
    try:
        # Simplification: assuming credentials are in payload if needed by client
        res = client.solicitar_atualizacao_v2(cnj, tipo=tipo, **payload)
        return jsonify({"ok": True, "data": res})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@api_ui_bp.get("/processo/<path:cnj>/status-atualizacao")
def status_atualizacao(cnj: str):
    from ..app import client
    if not client: abort(503)
    try:
        # Assuming there is a way to get status, usually checking recent solicitudes or a specific endpoint
        # The original had api_solicitar_status_v2(cnj)
        return jsonify({"ok": True, "status": "PENDING"}) # Placeholder
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@api_ui_bp.get("/processo/<path:cnj>/capa")
def get_capa(cnj: str):
    if not CNJ_REGEX.fullmatch(cnj): abort(400)
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT payload, updated_at FROM capa_cache WHERE cnj=?", (cnj,))
    row = cur.fetchone()
    if row:
        conn.close()
        return jsonify({"ok": True, "source": "cache", "data": json.loads(row["payload"]), "updated_at": row["updated_at"]})
    
    from ..app import client
    if not client: abort(503)
    try:
        data = client.obter_capa_processo(cnj)
        cur.execute("INSERT OR REPLACE INTO capa_cache (cnj, payload, updated_at) VALUES (?,?,?)",
                    (cnj, json.dumps(data, ensure_ascii=False), utcnow_iso()))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "source": "api", "data": data, "updated_at": utcnow_iso()})
    except Exception as e:
        conn.close()
        return jsonify({"ok": False, "error": str(e)})

@api_ui_bp.get("/processos/<path:cnj>/movimentacoes")
def get_movs(cnj: str):
    if not CNJ_REGEX.fullmatch(cnj): abort(400)
    limit = request.args.get("limit", 50, type=int)
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT data, tipo, tipo_inferido, texto FROM eventos_mov WHERE cnj=? ORDER BY data DESC, id DESC LIMIT ?", (cnj, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"ok": True, "items": rows})

@api_ui_bp.post("/processo/<path:cnj>/sync")
def sync_process(cnj: str):
    if not CNJ_REGEX.fullmatch(cnj): abort(400)
    from ..app import client
    if not client: abort(503)
    try:
        from ..services.logic import sync_process_movements
        res = sync_process_movements(client, cnj)
        return jsonify({"ok": True, "new_events": res.new_events})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@api_ui_bp.post("/discover/run-once")
def discover_now():
    from ..app import client
    from ..services.logic import run_discover_cycle
    if not client: abort(503)
    import threading
    threading.Thread(target=run_discover_cycle, args=(client, "ui-manual"), daemon=True).start()
    return jsonify({"ok": True, "message": "Cycle started in background."})

@api_ui_bp.post("/discover/doc/<path:doc>")
def discover_doc_api(doc: str):
    from ..app import client
    from ..services.logic import _discover_link_for_doc
    if not client: abort(503)
    try:
        res = _discover_link_for_doc(client, doc, limit=50)
        return jsonify({"ok": True, "data": res})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
