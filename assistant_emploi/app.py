"""Application Dash : layout global, onglets, routes Flask, enregistrement des callbacks."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from flask import abort, send_from_directory

from .config import ANNONCES_DIR, BASE_DIR, CONFIG, CV_DIR
from .database import init_db
from . import repository as repo
from .ui.home import candidatures_layout, dashboard_layout, stats_layout
from .ui.letters import letters_layout
from .ui.modals import all_modals
from .ui.sidebar import sidebar

# Base de données prête avant toute requête.
init_db()

app = dash.Dash(
    __name__,
    assets_folder=str(BASE_DIR / "assets"),
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    title=CONFIG.get("app_title", "Assistant Emploi"),
    update_title=None,
)
server = app.server


def _stores() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="refresh-apps", data=0),
            dcc.Store(id="refresh-letters", data=0),
            dcc.Store(id="edit-app-id", data=None),
            dcc.Store(id="status-app-id", data=None),
            dcc.Store(id="comment-edit-id", data=None),
            dcc.Store(id="selected-letter-id", data=None),
        ]
    )


# Pages disponibles (ordre = ordre de la barre latérale).
_PAGES = ("dashboard", "candidatures", "stats", "letters")


def _page_content(page: str) -> html.Div:
    if page == "candidatures":
        return candidatures_layout()
    if page == "stats":
        return stats_layout()
    if page == "letters":
        return letters_layout()
    return dashboard_layout()


app.layout = html.Div(
    id="app-container",
    className="app-shell",
    children=[
        _stores(),
        sidebar(active="dashboard"),
        html.Div(
            _page_content("dashboard"),
            id="page-content",
            className="main-area",
        ),
        all_modals(),
    ],
)


@app.callback(
    dash.Output("page-content", "children"),
    [dash.Output(f"nav-{p}", "className") for p in _PAGES],
    [dash.Input(f"nav-{p}", "n_clicks") for p in _PAGES],
    dash.Input({"type": "dash-see-all", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def _navigate(*_clicks):
    """Monte la page choisie dans la barre latérale et met à jour l'état actif."""
    trigger = dash.ctx.triggered_id or "nav-dashboard"
    if isinstance(trigger, dict) and trigger.get("type") == "dash-see-all":
        page = "candidatures"
    else:
        page = str(trigger).replace("nav-", "")
    classes = [
        "nav-item active" if p == page else "nav-item" for p in _PAGES
    ]
    return (_page_content(page), *classes)


# ---------------------------------------------------------------------------
# Routes Flask : copies locales d'annonces et téléchargement de CV
# ---------------------------------------------------------------------------

@server.route("/annonce/<int:app_id>")
def serve_annonce(app_id: int):
    application = repo.get_application(app_id)
    if application and application["annonce_path"]:
        file_path = ANNONCES_DIR / application["annonce_path"]
        if file_path.exists():
            return send_from_directory(str(ANNONCES_DIR), application["annonce_path"])
    return (
        "<!doctype html><meta charset='utf-8'><title>Copie indisponible</title>"
        "<body style='background:#1c1b19;color:#eae6df;font-family:sans-serif;"
        "padding:2rem'><h2>Copie locale indisponible</h2>"
        "<p>Cette annonce n'a pas pu être sauvegardée localement.</p></body>",
        404,
    )


@server.route("/cv/<int:cv_id>")
def serve_cv(cv_id: int):
    cv = repo.get_cv(cv_id)
    if not cv:
        abort(404)
    file_path = CV_DIR / cv["stored_filename"]
    if not file_path.exists():
        abort(404)
    return send_from_directory(
        str(CV_DIR),
        cv["stored_filename"],
        as_attachment=True,
        download_name=cv["original_filename"],
    )


# Enregistrement des callbacks (import après création de `app`).
from .callbacks import applications as _cb_applications  # noqa: E402,F401
from .callbacks import cvs as _cb_cvs  # noqa: E402,F401
from .callbacks import letters as _cb_letters  # noqa: E402,F401
