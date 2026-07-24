"""Chargement de la configuration et constantes de chemins.

Le fichier `config.json` (racine du projet) est éditable par l'utilisateur.
Les dossiers de données sont créés au premier import.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# Racine du projet = dossier parent du package.
BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = BASE_DIR / "config.json"

# Dossier de données : surchargé par la variable d'environnement
# ASSISTANT_EMPLOI_DATA_DIR (utile pour Docker et les tests).
_env_data_dir = os.environ.get("ASSISTANT_EMPLOI_DATA_DIR")
DATA_DIR = Path(_env_data_dir).expanduser() if _env_data_dir else BASE_DIR / "data"
CV_DIR = DATA_DIR / "cv"
ANNONCES_DIR = DATA_DIR / "annonces"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "assistant.db"

_DEFAULTS = {
    "home_recent_count": 10,
    "app_title": "Assistant Emploi",
    "default_status": "Candidature envoyée",
    "scraper": {
        "timeout_seconds": 20,
        "user_agent": (
            "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) "
            "Gecko/20100101 Firefox/125.0"
        ),
    },
    "host": "127.0.0.1",
    "port": 8050,
    "debug": True,
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config() -> dict:
    """Retourne la config fusionnée avec les valeurs par défaut."""
    data = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    return _deep_merge(_DEFAULTS, data)


def ensure_dirs() -> None:
    """Crée les dossiers de données s'ils n'existent pas."""
    for directory in (DATA_DIR, CV_DIR, ANNONCES_DIR, EXPORTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


CONFIG = load_config()
ensure_dirs()
