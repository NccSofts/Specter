import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Escavador API Configuration
ESCAVADOR_BASE = os.getenv("ESCAVADOR_BASE", "https://api.escavador.com/api/v2").rstrip("/")
ESCAVADOR_TOKEN = os.getenv("ESCAVADOR_TOKEN", "").strip()
WEBHOOK_AUTH_TOKEN = os.getenv("WEBHOOK_AUTH_TOKEN", "").strip()

# Database Configuration
DB_PATH = os.getenv("DB_PATH", "./escavador_monitor.db")
DB_PATH_ABS = os.path.abspath(DB_PATH)

# Application Performance and Behavior
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
AUTO_DISCOVER_ENABLED = os.getenv("AUTO_DISCOVER_ENABLED", "0").strip().lower() in ("1", "true", "yes", "on")
DISCOVER_INTERVAL_SECONDS = int(os.getenv("DISCOVER_INTERVAL_SECONDS", "3600"))
DISCOVER_LIMIT_PER_DOC = int(os.getenv("DISCOVER_LIMIT_PER_DOC", "50"))
DISCOVER_ONLY_IF_NO_LINKS = os.getenv("DISCOVER_ONLY_IF_NO_LINKS", "1").strip().lower() in ("1", "true", "yes", "on")
DISCOVER_MAX_DOCS_PER_CYCLE = int(os.getenv("DISCOVER_MAX_DOCS_PER_CYCLE", "50"))
CAPA_CACHE_TTL_SECONDS = int(os.getenv("CAPA_CACHE_TTL_SECONDS", "86400"))  # Default: 1 day

# Flask Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Sensitive Keys for Masking
SENSITIVE_ENV_KEYS = {"ESCAVADOR_TOKEN", "WEBHOOK_AUTH_TOKEN"}
