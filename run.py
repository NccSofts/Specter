import sys
import os

# Add current directory to path to allow absolute imports of specter_app
sys.path.insert(0, os.path.abspath(os.curdir))

from specter_app.app import create_app, start_background_threads, client
from specter_app.config import HOST, PORT
from specter_app.utils.logger import logger

if __name__ == "__main__":
    app = create_app()
    start_background_threads(client)
    logger.info(f"Specter Modular Runner starting on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=True, use_reloader=False)
