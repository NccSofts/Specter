import re
import json
import sqlite3
import requests
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set
from ..database import db_connect, upsert_processo, link_doc_process, record_api_usage, ensure_process_registered
from ..utils.logger import logger
from ..utils.helpers import utcnow_iso, stable_hash, normalize_doc, doc_type, extract_list, CNJ_REGEX, DOC_REGEX
from ..utils.state import set_discover_state, get_discover_state, DISCOVER_STATE_LOCK, DISCOVER_STATE, stop_flag
from ..clients.escavador import EscavadorClient
from ..config import (
    DISCOVER_MAX_DOCS_PER_CYCLE,
    DISCOVER_ONLY_IF_NO_LINKS,
    DISCOVER_LIMIT_PER_DOC,
    ESCAVADOR_TOKEN
)

@dataclass
class ProcessResult:
    cnj: str
    new_events: int

KEYWORDS = [
    ("CITACAO", [r"\bcita", r"\bcitação", r"\bcitacao"]),
    ("INTIMACAO", [r"\bintim", r"\bintimação", r"\bintimacao"]),
    ("SENTENCA", [r"\bsenten", r"\bsentença", r"\bsentenca"]),
    ("DECISAO", [r"\bdecis", r"\bdecisão", r"\bdecisao"]),
    ("DESPACHO", [r"\bdespach"]),
    ("AUDIENCIA", [r"\baudi", r"\baudiência", r"\baudiencia"]),
    ("JUNTADA", [r"\bjuntad"]),
    ("DISTRIBUICAO", [r"\bdistribu", r"\bdistribuição", r"\bdistribuicao"]),
    ("PENHORA", [r"\bpenhor"]),
    ("TRANSITO", [r"\btr[âa]nsit", r"\btransit"]),
]

def infer_tipo(texto: str) -> Optional[str]:
    if not texto: return None
    for label, patterns in KEYWORDS:
        for p in patterns:
            if re.search(p, texto, flags=re.IGNORECASE):
                return label
    return None

def mov_to_hash(mov: Dict[str, Any]) -> str:
    for key in ("id", "codigo", "uuid", "hash"):
        if mov.get(key): return f"id:{mov[key]}"
    core = {
        "data": mov.get("data") or mov.get("data_hora") or mov.get("dataHora") or mov.get("dataHoraCadastro"),
        "texto": mov.get("texto") or mov.get("descricao") or mov.get("conteudo"),
        "tipo": mov.get("tipo") or mov.get("tipo_movimentacao") or mov.get("tipoMovimentacao"),
    }
    return stable_hash(core)

def parse_cnj_candidates(payload: Dict[str, Any]) -> List[str]:
    cnjs: List[str] = []
    def scan(o: Any):
        if isinstance(o, dict):
            for _, v in o.items():
                if isinstance(v, (dict, list)): scan(v)
                elif isinstance(v, str):
                    m = CNJ_REGEX.search(v)
                    if m: cnjs.append(m.group(0))
        elif isinstance(o, list):
            for x in o: scan(x)
    scan(payload)
    out: List[str] = []
    seen: Set[str] = set()
    for c in cnjs:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out

def parse_doc_candidates(payload: Dict[str, Any]) -> List[str]:
    docs: List[str] = []
    def add_doc(s: str):
        m = DOC_REGEX.search(s or "")
        if not m: return
        raw = m.group(1)
        digits = re.sub(r"\D", "", raw)
        if len(digits) in (11, 14): docs.append(raw)
    def scan(o: Any):
        if isinstance(o, dict):
            for _, v in o.items():
                if isinstance(v, (dict, list)): scan(v)
                elif isinstance(v, str): add_doc(v)
        elif isinstance(o, list):
            for x in o: scan(x)
    scan(payload)
    out: List[str] = []
    seen: Set[str] = set()
    for d in docs:
        key = re.sub(r"\D", "", d)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out

def save_mov_events(conn: sqlite3.Connection, cnj: str, movs: List[Dict[str, Any]]) -> int:
    cur = conn.cursor()
    new_count = 0
    for mov in movs:
        event_hash = mov_to_hash(mov)
        texto = str(mov.get("texto") or mov.get("descricao") or mov.get("conteudo") or "")
        tipo = mov.get("tipo") or mov.get("tipo_movimentacao") or mov.get("tipoMovimentacao")
        tipo_inf = infer_tipo(texto)
        data = mov.get("data") or mov.get("data_hora") or mov.get("dataHora") or mov.get("dataHoraCadastro")
        raw = json.dumps(mov, ensure_ascii=False)
        try:
            cur.execute(
                "INSERT INTO eventos_mov (cnj, event_hash, data, tipo, tipo_inferido, texto, raw_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (cnj, event_hash, data, tipo, tipo_inf, texto, raw, utcnow_iso()),
            )
            new_count = new_count + 1
        except sqlite3.IntegrityError:
            continue
    if new_count > 0:
        cur.execute("UPDATE processos SET last_event_at=?, last_sync_at=? WHERE cnj=?", (utcnow_iso(), utcnow_iso(), cnj))
    else:
        cur.execute("UPDATE processos SET last_sync_at=? WHERE cnj=?", (utcnow_iso(), cnj))
    conn.commit()
    return new_count

def sync_process_movements(client: EscavadorClient, cnj: str, limit: int = 300) -> ProcessResult:
    data = client.listar_movimentacoes(cnj, limit=limit)
    movs = extract_list(data)
    conn = db_connect()
    ensure_process_registered(conn, cnj)
    new_events = save_mov_events(conn, cnj, movs)
    conn.close()
    return ProcessResult(cnj=cnj, new_events=new_events)

def ingest_callback(source: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    h = stable_hash(payload)
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO callback_inbox (source, payload_hash, payload_json, received_at) VALUES (?, ?, ?, ?)",
            (source, h, json.dumps(payload, ensure_ascii=False), utcnow_iso()),
        )
        conn.commit()
        return True, h
    except sqlite3.IntegrityError:
        return False, h
    except Exception:
        return False, h
    finally:
        conn.close()

def process_inbox_once(client: EscavadorClient, max_items: int = 25) -> Dict[str, Any]:
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT id, payload_json FROM callback_inbox WHERE status='PENDING' ORDER BY id ASC LIMIT ?", (max_items,))
    rows = cur.fetchall()
    conn.close()
    
    processed: int = 0
    errors: int = 0
    cnj_synced: Dict[str, int] = {}
    linked: List[Dict[str, str]] = []
    
    for row in rows:
        inbox_id = row["id"]
        payload = json.loads(row["payload_json"] or "{}")
        try:
            cnjs = parse_cnj_candidates(payload)
            docs = parse_doc_candidates(payload)
            for cnj in cnjs:
                try: client.criar_monitor_processo(cnj)
                except requests.HTTPError as e: logger.warning("criar_monitor_processo(%s) warning: %s", cnj, str(e))
                res = sync_process_movements(client, cnj, limit=400)
                cnj_synced[cnj] = int(cnj_synced.get(cnj, 0)) + int(res.new_events)
                if docs:
                    conn3 = db_connect()
                    for d in docs:
                        try: dnorm = str(normalize_doc(d))
                        except Exception: continue
                        link_doc_process(conn3, dnorm, cnj)
                        linked.append({"doc": dnorm, "cnj": cnj})
                    conn3.close()
            
            conn2 = db_connect()
            cur2 = conn2.cursor()
            cur2.execute("UPDATE callback_inbox SET status='PROCESSED', processed_at=? WHERE id=?", (utcnow_iso(), inbox_id))
            conn2.commit()
            conn2.close()
            processed = int(processed) + 1
        except Exception as ex:
            logger.exception("Failed processing inbox id=%s", inbox_id)
            conn3 = db_connect()
            cur3 = conn3.cursor()
            cur3.execute("UPDATE callback_inbox SET status='ERROR', processed_at=?, error=? WHERE id=?", (utcnow_iso(), str(ex)[:1000], inbox_id))
            conn3.commit()
            conn3.close()
            errors = int(errors) + 1
            
    return {"processed": processed, "errors": errors, "cnj_new_events": cnj_synced, "linked": linked}

def _get_watchlist_docs(conn) -> List[str]:
    cur = conn.cursor()
    cur.execute("SELECT doc FROM watchlist ORDER BY id ASC")
    return [r["doc"] for r in cur.fetchall() if r["doc"]]

def _doc_has_links(conn: sqlite3.Connection, doc: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM doc_process WHERE doc=? LIMIT 1", (doc,))
    return cur.fetchone() is not None

def _discover_link_for_doc(client: EscavadorClient, doc: str, limit: int) -> dict:
    docn = normalize_doc(doc)
    resp = client.listar_processos_envolvido(docn, limit=limit, page=1)
    processos = extract_list(resp)
    if not processos and isinstance(resp, dict) and isinstance(resp.get("processos"), list):
        processos = resp["processos"]
    discovered: List[str] = []
    inserted_processos: int = 0
    linked: int = 0
    conn = db_connect()
    try:
        for p in processos:
            if not isinstance(p, dict): continue
            cnj = (p.get("numero_cnj") or p.get("numero") or p.get("cnj") or "").strip()
            if not cnj or not CNJ_REGEX.fullmatch(cnj): continue
            discovered.append(cnj)
            if upsert_processo(conn, cnj): inserted_processos += 1
            if link_doc_process(conn, docn, cnj): linked += 1
    finally: conn.close()
    return {"doc": docn, "discovered": len(discovered), "inserted_processos": inserted_processos, "linked": linked}

def run_discover_cycle(client: EscavadorClient, trigger: str = "manual") -> Dict[str, Any]:
    if client is None: raise RuntimeError("Client não inicializado.")
    with DISCOVER_STATE_LOCK:
        if DISCOVER_STATE.get("running"):
            return {"ok": False, "error": "ALREADY_RUNNING", "state": get_discover_state()}
        set_discover_state(running=True, last_trigger=trigger, last_started=utcnow_iso(), last_error=None, last_totals=None, last_finished=None)

    totals = {"docs": 0, "ran_docs": 0, "discovered": 0, "inserted_processos": 0, "linked": 0, "skipped": 0, "errors": 0}
    conn = db_connect()
    try:
        all_docs = _get_watchlist_docs(conn)
        limit_val = DISCOVER_MAX_DOCS_PER_CYCLE if DISCOVER_MAX_DOCS_PER_CYCLE is not None else 1
        limit_docs = max(int(limit_val), 1)
        docs = all_docs[:limit_docs]
        conn.close()

        for doc in docs:
            if stop_flag.is_set(): break
            totals["docs"] = int(totals.get("docs", 0)) + 1
            try:
                conn_d = db_connect()
                is_linked = False
                try:
                    if DISCOVER_ONLY_IF_NO_LINKS and _doc_has_links(conn_d, doc):
                        is_linked = True
                finally: conn_d.close()
                
                if is_linked:
                    totals["skipped"] = int(totals.get("skipped", 0)) + 1
                    continue

                st = _discover_link_for_doc(client, doc, limit=max(int(DISCOVER_LIMIT_PER_DOC or 1), 1))
                totals["ran_docs"] = int(totals.get("ran_docs", 0)) + 1
                totals["discovered"] = int(totals.get("discovered", 0)) + int(st.get("discovered", 0))
                totals["inserted_processos"] = int(totals.get("inserted_processos", 0)) + int(st.get("inserted_processos", 0))
                totals["linked"] = int(totals.get("linked", 0)) + int(st.get("linked", 0))
            except Exception:
                totals["errors"] = int(totals.get("errors", 0)) + 1
                logger.exception("Discover cycle failed for doc=%s", doc)

        logger.info("Discover cycle (%s): ran_docs=%s total=%s", trigger, totals["ran_docs"], totals["docs"])
        set_discover_state(last_totals=totals, last_finished=utcnow_iso())
        return {"ok": True, "totals": totals, "state": get_discover_state()}
    except Exception as e:
        logger.exception("Discover cycle failed")
        set_discover_state(last_error=str(e), last_finished=utcnow_iso())
        return {"ok": False, "error": "CYCLE_FAILED", "message": str(e), "state": get_discover_state()}
    finally:
        set_discover_state(running=False)
