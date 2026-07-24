"""Téléchargement de la copie locale d'une annonce.

Best-effort : de nombreux job-boards bloquent le scraping ou exigent du JavaScript.
On enregistre ce qu'on obtient et on remonte le succès/échec sans lever d'exception.
"""
from __future__ import annotations

from urllib.parse import urlparse

import requests

from .config import ANNONCES_DIR, CONFIG


def is_http_url(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = urlparse(value.strip())
    except (ValueError, AttributeError):
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _inject_base_tag(html: str, url: str) -> str:
    """Injecte une balise <base> pour que CSS/images relatifs pointent vers l'origine."""
    base_tag = f'<base href="{url}">'
    lower = html.lower()
    idx = lower.find("<head")
    if idx != -1:
        end = lower.find(">", idx)
        if end != -1:
            return html[: end + 1] + base_tag + html[end + 1 :]
    # Pas de <head> : on préfixe.
    return base_tag + html


def download_annonce(url: str, app_id: int) -> tuple[bool, str | None, str]:
    """Télécharge `url` et l'enregistre dans data/annonces/<app_id>.html.

    Renvoie (ok, chemin_relatif, message).
    """
    if not is_http_url(url):
        return (False, None, "URL non téléchargeable")

    scraper_cfg = CONFIG.get("scraper", {})
    headers = {
        "User-Agent": scraper_cfg.get("user_agent", "Mozilla/5.0"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }
    timeout = scraper_cfg.get("timeout_seconds", 20)

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        return (False, None, f"Échec du téléchargement : {exc}")

    content_type = response.headers.get("Content-Type", "")
    filename = f"{app_id}.html"
    dest = ANNONCES_DIR / filename

    try:
        if "html" in content_type.lower() or not content_type:
            response.encoding = response.encoding or "utf-8"
            html = _inject_base_tag(response.text, url)
            dest.write_text(html, encoding="utf-8", errors="replace")
        else:
            # Contenu non-HTML (PDF, etc.) : on écrit une page enveloppe avec un lien.
            wrapper = (
                f'<!doctype html><meta charset="utf-8">'
                f'<title>Annonce</title>'
                f'<p>Contenu non-HTML ({content_type}). '
                f'<a href="{url}">Ouvrir l\'annonce d\'origine</a></p>'
            )
            dest.write_text(wrapper, encoding="utf-8")
    except OSError as exc:
        return (False, None, f"Écriture impossible : {exc}")

    return (True, filename, "Copie locale enregistrée")
