import sqlite3
import hashlib
import json
from urllib.parse import unquote_plus
import re
from typing import Any, Optional, Dict
from .config import DB_PATH
from .utils.logger import logger
from .utils.helpers import utcnow_iso

# Global Lock for thread-safe state (inherited from original script if needed)
# Actually, the original used local connections in each function, which is safer for SQLite in threads.

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def db_init() -> None:
    conn = db_connect()
    cur = conn.cursor()

    tables = [
        """CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc TEXT NOT NULL UNIQUE,
            tipo_doc TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS processos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnj TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            last_sync_at TEXT,
            last_event_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS eventos_mov (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnj TEXT NOT NULL,
            event_hash TEXT NOT NULL,
            data TEXT,
            tipo TEXT,
            tipo_inferido TEXT,
            texto TEXT,
            raw_json TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(cnj, event_hash)
        )""",
        """CREATE TABLE IF NOT EXISTS callback_inbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            payload_hash TEXT NOT NULL UNIQUE,
            payload_json TEXT NOT NULL,
            received_at TEXT NOT NULL,
            processed_at TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            error TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS doc_process (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc TEXT NOT NULL,
            cnj TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(doc, cnj)
        )""",
        """CREATE TABLE IF NOT EXISTS alert_state (
            doc TEXT PRIMARY KEY,
            last_event_id INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS capa_cache (
            cnj TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            doc TEXT,
            cnj TEXT,
            service_key TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            http_status INTEGER,
            items_count INTEGER NOT NULL DEFAULT 0,
            cost_brl REAL NOT NULL DEFAULT 0.0,
            notes TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS api_usage_real (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            doc TEXT,
            cnj TEXT,
            method TEXT,
            endpoint TEXT NOT NULL,
            cost_brl REAL NOT NULL,
            raw_line TEXT,
            fingerprint TEXT UNIQUE,
            imported_at TEXT,
            source TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS pricing (
            service_key TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            base_cost_brl REAL NOT NULL,
            step_cost_brl REAL NOT NULL DEFAULT 0.0,
            step_items INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS docs_v2_cache(
            cnj TEXT NOT NULL,
            tipo TEXT NOT NULL,
            limit_n INTEGER NOT NULL,
            page_n INTEGER NOT NULL,
            items_json TEXT NOT NULL,
            links_json TEXT,
            paginator_json TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(cnj,tipo,limit_n,page_n)
        )""",
        """CREATE TABLE IF NOT EXISTS updates_v2(
            cnj TEXT NOT NULL,
            tipo TEXT NOT NULL,
            request_json TEXT,
            response_json TEXT,
            status_json TEXT,
            status TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(cnj,tipo)
        )"""
    ]

    for sql in tables:
        cur.execute(sql)

    # Indices
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_api_usage_ts ON api_usage (ts)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_doc_ts ON api_usage (doc, ts)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_cnj_ts ON api_usage (cnj, ts)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_service_ts ON api_usage (service_key, ts)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_real_ts ON api_usage_real (ts)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_real_imported_at ON api_usage_real (imported_at)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_real_doc_ts ON api_usage_real (doc, ts)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_real_cnj_ts ON api_usage_real (cnj, ts)",
        "CREATE INDEX IF NOT EXISTS idx_eventos_cnj_id ON eventos_mov (cnj, id)",
        "CREATE INDEX IF NOT EXISTS idx_doc_process_doc ON doc_process (doc)",
        "CREATE INDEX IF NOT EXISTS idx_doc_process_cnj ON doc_process (cnj)",
        "CREATE INDEX IF NOT EXISTS idx_inbox_status ON callback_inbox (status, id)"
    ]
    for sql in indices:
        cur.execute(sql)

    conn.commit()
    conn.close()

# Pricing and Usage Utils
PRICING_DEFAULTS = {
    "v2_capa_processo": {"model": "FIXED", "base": 0.04},
    "v2_movimentacoes_processo": {"model": "FIXED", "base": 0.04},
    "v2_processos_envolvido": {"model": "ITEMS200", "base": 2.90, "step": 0.05, "step_items": 200},
    "v2_resumo_envolvido": {"model": "FIXED", "base": 0.35},
    "v2_resumo_processo_ia": {"model": "FIXED", "base": 0.04},
}

def _pricing_for(service_key: str) -> dict:
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("SELECT model, base_cost_brl, step_cost_brl, step_items FROM pricing WHERE service_key=?", (service_key,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                "model": row["model"],
                "base": float(row["base_cost_brl"]),
                "step": float(row["step_cost_brl"]),
                "step_items": int(row["step_items"]),
            }
    except Exception:
        pass
    return PRICING_DEFAULTS.get(service_key, {"model": "FIXED", "base": 0.0})

def estimate_cost_brl(service_key: str, *, items_upto: int = 0) -> float:
    p = _pricing_for(service_key)
    model = (p.get("model") or "FIXED").upper()
    base = float(p.get("base") or 0.0)
    if model == "ITEMS200":
        step = float(p.get("step") or 0.0)
        step_items = int(p.get("step_items") or 200) or 200
        if items_upto <= 0:
            return base
        batches = (items_upto + step_items - 1) // step_items
        return base + step * max(0, batches - 1)
    return base

def record_api_usage(*, doc: Optional[str] = None, cnj: Optional[str] = None, service_key: str, endpoint: str, http_status: Optional[int] = None, items_count: int = 0, cost_brl: float = 0.0, notes: str = "") -> None:
    try:
        conn = db_connect()
        cur = conn.cursor()
        safe_notes = str(notes or "")
        if len(safe_notes) > 500: safe_notes = safe_notes[:500]
        cur.execute(
            "INSERT INTO api_usage (ts, doc, cnj, service_key, endpoint, http_status, items_count, cost_brl, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (utcnow_iso(), doc, cnj, service_key, endpoint, http_status, int(items_count or 0), float(cost_brl or 0.0), safe_notes),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Falha ao registrar api_usage")

def _extract_doc_from_endpoint(ep: str) -> Optional[str]:
    m = re.search(r"(?:\?|&)cpf_cnpj=([^&]+)", ep)
    if not m: return None
    raw = m.group(1)
    try:
        raw = unquote_plus(str(raw))
    except Exception:
        raw = str(raw)
    digits = re.sub(r"\D", "", raw)
    return digits if len(digits) in (11, 14) else None

def _extract_cnj_from_endpoint(ep: str) -> Optional[str]:
    m = re.search(r"/processos/numero_cnj/([^/?]+)", ep)
    return m.group(1) if m else None

def _fingerprint_usage(ts_iso: str, method: str, endpoint: str, cost_brl: float) -> str:
    s = f"{ts_iso}|{method}|{endpoint}|{float(cost_brl):.6f}"
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def record_api_usage_real(*, ts_iso: str, doc: Optional[str] = None, cnj: Optional[str] = None, method: str, endpoint: str, cost_brl: float, raw_line: str, source: str = "xlsx", imported_at: Optional[str] = None) -> None:
    try:
        fp = _fingerprint_usage(ts_iso, method, endpoint, float(cost_brl))
        imp_at = imported_at or utcnow_iso()
        conn = db_connect()
        cur = conn.cursor()
        safe_line = str(raw_line or "")
        if len(safe_line) > 800: safe_line = safe_line[:800]
        cur.execute(
            "INSERT OR IGNORE INTO api_usage_real (ts, doc, cnj, method, endpoint, cost_brl, raw_line, fingerprint, imported_at, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ts_iso, doc, cnj, method, endpoint, float(cost_brl), safe_line, fp, imp_at, source),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Falha ao registrar api_usage_real")

def ensure_process_registered(conn: sqlite3.Connection, cnj: str) -> None:
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO processos (cnj, created_at) VALUES (?, ?)", (cnj, utcnow_iso()))
    conn.commit()

def upsert_processo(conn: sqlite3.Connection, cnj: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT id FROM processos WHERE cnj=?", (cnj,))
    if cur.fetchone(): return False
    cur.execute("INSERT INTO processos (cnj, created_at) VALUES (?, ?)", (cnj, utcnow_iso()))
    conn.commit()
    return True

def link_doc_process(conn: sqlite3.Connection, doc: str, cnj: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM doc_process WHERE doc=? AND cnj=?", (doc, cnj))
    if cur.fetchone(): return False
    cur.execute("INSERT OR IGNORE INTO doc_process (doc, cnj, created_at) VALUES (?, ?, ?)", (doc, cnj, utcnow_iso()))
    conn.commit()
    return True
