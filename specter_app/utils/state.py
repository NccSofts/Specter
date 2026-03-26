import threading
from typing import Any, Dict, Optional
from .helpers import utcnow_iso

# Discovery State
DISCOVER_STATE_LOCK = threading.Lock()
DISCOVER_STATE: Dict[str, Any] = {
    "running": False,
    "last_trigger": None,
    "last_started": None,
    "last_finished": None,
    "last_totals": None,
    "last_error": None,
}

def set_discover_state(**kwargs: Any) -> None:
    with DISCOVER_STATE_LOCK:
        for k, v in kwargs.items():
            DISCOVER_STATE[k] = v

def get_discover_state() -> Dict[str, Any]:
    with DISCOVER_STATE_LOCK:
        return dict(DISCOVER_STATE)

# Polling State
POLL_STATE_LOCK = threading.Lock()
POLL_STATE: Dict[str, Any] = {
    "running": False,
    "last_started": None,
    "last_finished": None,
    "last_totals": None,
    "last_error": None,
}

def set_poll_state(**kwargs: Any) -> None:
    with POLL_STATE_LOCK:
        for k, v in kwargs.items():
            POLL_STATE[k] = v

def get_poll_state() -> Dict[str, Any]:
    with POLL_STATE_LOCK:
        return dict(POLL_STATE)

# API Error Tracking
API_ERROR_LOCK = threading.Lock()
LAST_API_ERROR: Dict[str, Any] = {
    "at": None,
    "method": None,
    "path": None,
    "status": None,
    "message": None,
}

def set_last_api_error(method: str, path: str, status: Optional[int], message: str) -> None:
    with API_ERROR_LOCK:
        LAST_API_ERROR["at"] = utcnow_iso()
        LAST_API_ERROR["method"] = method
        LAST_API_ERROR["path"] = path
        LAST_API_ERROR["status"] = status
        LAST_API_ERROR["message"] = (message or "")[:800]

def get_last_api_error() -> Dict[str, Any]:
    with API_ERROR_LOCK:
        return dict(LAST_API_ERROR)

# Threading control
stop_flag = threading.Event()
