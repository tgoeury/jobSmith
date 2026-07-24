"""Point d'entrée : lance le serveur Dash.

    python run.py
"""
from assistant_emploi.app import app
from assistant_emploi.config import CONFIG

if __name__ == "__main__":
    app.run(
        host=CONFIG.get("host", "127.0.0.1"),
        port=CONFIG.get("port", 8050),
        debug=CONFIG.get("debug", True),
    )
