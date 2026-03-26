import re
from typing import Optional

EXTRATO_LINE_RE = re.compile(
    r"^(GET|POST|PUT|DELETE)\s+(\S+)\s+R\$\s*([+-]?[\d\.,]+)\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s*$"
)

def parse_brl_value(s: str) -> float:
    try:
        clean = s.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return float(clean)
    except (ValueError, AttributeError):
        return 0.0
