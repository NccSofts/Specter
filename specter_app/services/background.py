import time
from ..config import POLL_INTERVAL_SECONDS, DISCOVER_INTERVAL_SECONDS, AUTO_DISCOVER_ENABLED, ESCAVADOR_TOKEN
from ..utils.logger import logger
from ..utils.helpers import utcnow_iso, extract_list
from ..utils.state import set_poll_state, set_discover_state, stop_flag
from .logic import process_inbox_once, ingest_callback, run_discover_cycle
from ..clients.escavador import EscavadorClient

def poll_callbacks_loop(client: EscavadorClient):
    logger.info("Polling loop started (interval=%ss)", POLL_INTERVAL_SECONDS)
    while not stop_flag.is_set():
        set_poll_state(running=True, last_started=utcnow_iso(), last_error=None)
        try:
            data = client.listar_callbacks(limit=100, page=1)
            callbacks = extract_list(data)

            inserted = 0
            for cb in callbacks:
                ins, _ = ingest_callback("poll", cb)
                if ins:
                    inserted += 1

            pr = process_inbox_once(client, max_items=50)
            logger.info(
                "Poll: inserted=%s processed=%s errors=%s",
                inserted,
                pr["processed"],
                pr["errors"]
            )
            set_poll_state(
                last_totals={
                    "inserted": inserted,
                    "processed": pr["processed"],
                    "errors": pr["errors"],
                    "linked": len(pr.get("linked", []))
                },
                last_finished=utcnow_iso()
            )
        except Exception as e:
            logger.exception("Polling failed")
            set_poll_state(last_error=str(e), last_finished=utcnow_iso())
        finally:
            set_poll_state(running=False)

        stop_flag.wait(POLL_INTERVAL_SECONDS)

def auto_discover_loop(client: EscavadorClient):
    if DISCOVER_INTERVAL_SECONDS <= 0:
        logger.info("Auto-discover desabilitado.")
        return
    logger.info("Auto-discover loop started")

    while not stop_flag.is_set():
        if not AUTO_DISCOVER_ENABLED:
            stop_flag.wait(min(DISCOVER_INTERVAL_SECONDS, 10))
            continue

        if not ESCAVADOR_TOKEN:
            logger.info("Auto-discover pausado: token ausente.")
            stop_flag.wait(DISCOVER_INTERVAL_SECONDS)
            continue

        try:
            run_discover_cycle(client, trigger="auto")
        except Exception:
            logger.exception("Auto-discover cycle failed")

        stop_flag.wait(DISCOVER_INTERVAL_SECONDS)
