import os
import re
import logging
from ..config import SENSITIVE_ENV_KEYS, LOG_LEVEL

def _mask(s: str) -> str:
    if not s:
        return s
    if len(s) <= 12:
        return "*" * len(s)
    return s[:6] + "…" + s[-6:]

def redact_secrets(text: str) -> str:
    if not text:
        return text
    out = text
    for k in SENSITIVE_ENV_KEYS:
        v = os.getenv(k, "")
        if v:
            out = out.replace(v, _mask(v))
    out = re.sub(r"Bearer\s+[A-Za-z0-9\-\._]+", "Bearer ***", out)
    return out

class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        return redact_secrets(msg)

def setup_logger(name: str = "escavador_monitor") -> logging.Logger:
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger

logger = setup_logger()
