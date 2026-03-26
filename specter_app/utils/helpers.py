import re
import json
import hashlib
import html as _html_mod
from datetime import datetime, timezone
from typing import Any

# Markdown → HTML (with fallbacks)
try:
    import markdown as _md
    def md_to_html(text: str) -> str:
        return _md.markdown(text, extensions=["tables", "fenced_code"])
except ImportError:
    try:
        import mistune
        def md_to_html(text: str) -> str:
            return mistune.html(text)
    except ImportError:
        def md_to_html(text: str) -> str:
            return "<pre class='wrap-any p-3'>" + _html_mod.escape(text) + "</pre>"

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def stable_hash(obj: Any) -> str:
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def normalize_doc(doc: str) -> str:
    digits = re.sub(r"\D", "", doc or "")
    if len(digits) in (11, 14):
        return doc.strip()
    raise ValueError("Documento inválido. Informe CPF (11 dígitos) ou CNPJ (14 dígitos).")

def doc_type(doc: str) -> str:
    digits = re.sub(r"\D", "", doc)
    return "CNPJ" if len(digits) == 14 else "CPF"

CNJ_REGEX = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
DOC_REGEX = re.compile(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b")

def extract_list(data: Any) -> list:
    """Helper to extract list from Escavador API response 'items' or similar."""
    if isinstance(data, dict):
        return data.get("items", []) or data.get("data", []) or []
    if isinstance(data, list):
        return data
    return []
