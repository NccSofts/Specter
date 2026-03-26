import threading
from flask import Flask, redirect, jsonify
from .config import HOST, PORT, ESCAVADOR_TOKEN, ESCAVADOR_BASE, POLL_INTERVAL_SECONDS, AUTO_DISCOVER_ENABLED
from .database import db_init
from .clients.escavador import EscavadorClient
from .routes.ui import ui_bp
from .routes.api_v2 import api_v2_bp
from .routes.api_ui import api_ui_bp
from .routes.webhooks import webhooks_bp
from .routes.costs import costs_bp
from .services.background import poll_callbacks_loop, auto_discover_loop
from .utils.logger import logger
from .utils.helpers import utcnow_iso

# Global Client (accessible by Blueprints via 'from ..app import client')
client = EscavadorClient(ESCAVADOR_BASE, ESCAVADOR_TOKEN) if ESCAVADOR_TOKEN else None

def create_app():
    app = Flask(__name__)
    
    # Initialize DB
    db_init()
    
    # Register Blueprints
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_v2_bp, url_prefix="/api/v2")
    app.register_blueprint(api_ui_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(costs_bp)

    @app.get("/")
    def home():
        return redirect("/ui")

    @app.get("/health")
    def health():
        return jsonify({
            "ok": True, 
            "token": bool(ESCAVADOR_TOKEN),
            "time": utcnow_iso()
        })

    return app

def start_background_threads(esc_client):
    if not esc_client:
        logger.warning("Background threads NOT started: Escavador Client not ready (No token?)")
        return
    
    logger.info("Starting background threads...")
    t1 = threading.Thread(target=poll_callbacks_loop, args=(esc_client,), daemon=True)
    t1.start()
    
    if AUTO_DISCOVER_ENABLED:
        t2 = threading.Thread(target=auto_discover_loop, args=(esc_client,), daemon=True)
        t2.start()

if __name__ == "__main__":
    app = create_app()
    start_background_threads(client)
    logger.info(f"Specter Modular starting on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
