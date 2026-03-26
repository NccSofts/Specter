import re
from flask import Blueprint, jsonify, request, abort
from ..database import db_connect, record_api_usage_real, _extract_doc_from_endpoint, _extract_cnj_from_endpoint
from ..utils.costs import EXTRATO_LINE_RE, parse_brl_value
from ..utils.logger import logger
from ..utils.helpers import utcnow_iso

costs_bp = Blueprint("costs", __name__, url_prefix="/ui/api/costs")

@costs_bp.get("/metrics")
def get_costs_metrics():
    # Placeholder for cost aggregation logic
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT SUM(cost_brl) as total FROM api_usage")
    est = cur.fetchone()["total"] or 0.0
    cur.execute("SELECT SUM(cost_brl) as total FROM api_usage_real")
    real = cur.fetchone()["total"] or 0.0
    conn.close()
    return jsonify({"ok": True, "estimated": est, "real": real, "delta": real - est})

@costs_bp.post("/import")
def import_costs():
    payload = request.get_json(force=True, silent=True) or {}
    raw_text = payload.get("text", "")
    source = payload.get("source", "manual")
    if not raw_text: abort(400, description="Campo 'text' é obrigatório.")
    
    lines = raw_text.splitlines()
    count: int = 0
    errors: int = 0
    
    for line in lines:
        line = line.strip()
        if not line: continue
        m = EXTRATO_LINE_RE.match(line)
        if not m:
            errors = errors + 1; continue
            
        method, endpoint, cost_str, date_str, time_str = m.groups()
        cost = parse_brl_value(cost_str)
        # Parse date components
        day, month, year = date_str.split("/")
        ts_iso = f"{year}-{month}-{day}T{time_str}:00Z"
        
        doc = _extract_doc_from_endpoint(endpoint)
        cnj = _extract_cnj_from_endpoint(endpoint)
        
        try:
            record_api_usage_real(
                ts_iso=ts_iso,
                doc=doc,
                cnj=cnj,
                method=method,
                endpoint=endpoint,
                cost_brl=cost,
                raw_line=line,
                source=source
            )
            count = count + 1
        except Exception:
            errors = errors + 1
            
    return jsonify({"ok": True, "count": count, "errors": errors})
