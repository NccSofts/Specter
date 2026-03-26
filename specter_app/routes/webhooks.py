from flask import Blueprint, request, jsonify, abort
from ..config import WEBHOOK_AUTH_TOKEN
from ..services.logic import ingest_callback
from ..utils.logger import logger

webhooks_bp = Blueprint("webhooks", __name__)

@webhooks_bp.post("/webhook")
def webhook_receiver():
    # Verify token
    token = request.headers.get("Authorization")
    if WEBHOOK_AUTH_TOKEN and token != f"Bearer {WEBHOOK_AUTH_TOKEN}":
        logger.warning("Webhook unauthorized: invalid token.")
        abort(401)
    
    payload = request.get_json(silent=True) or {}
    source = request.args.get("source", "webhook")
    
    ok, hash_id = ingest_callback(source, payload)
    return jsonify({"ok": ok, "hash": hash_id})

@webhooks_bp.post("/callback")
def escavador_callback():
    # Escavador internal callback format (doesn't always use the same auth)
    # We'll trust it for now or implement specific verification if needed
    payload = request.get_json(silent=True) or {}
    ok, hash_id = ingest_callback("escavador_callback", payload)
    return jsonify({"ok": ok, "hash": hash_id})
