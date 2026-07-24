"""Application Dash : layout global, onglets, routes Flask, enregistrement des callbacks."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from flask import abort, send_from_directory

from .config import ANNONCES_DIR, BASE_DIR, CONFIG, CV_DIR
from .database import init_db
from . import repository as repo
from .ui.home import home_layout
from .ui.letters import letters_layout
from .ui.modals import all_modals

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


# Styles des onglets (dcc.Tabs) — thème anthracite / ambre en inline pour éviter
# tout conflit avec les styles par défaut clairs de dcc.Tabs.
_TAB_STYLE = {
    "backgroundColor": "transparent",
    "border": "none",
    "borderBottom": "1px solid #3a362f",
    "color": "#a49e92",
    "padding": "0.6rem 1.1rem",
}
_TAB_SELECTED = {
    "backgroundColor": "transparent",
    "border": "none",
    "borderBottom": "2px solid #d9843a",
    "color": "#d9843a",
    "fontWeight": "600",
    "padding": "0.6rem 1.1rem",
}


app.layout = html.Div(
    id="app-container",
    children=[
        _stores(),
        html.Div(
            className="app-header",
            children=[
                html.H1(
                    [html.Span("● ", className="accent-bar"),
                     CONFIG.get("app_title", "Assistant Emploi")]
                ),
            ],
        ),
        dcc.Tabs(
            id="main-tabs",
            value="tab-home",
            children=[
                dcc.Tab(label="Accueil", value="tab-home",
                        style=_TAB_STYLE, selected_style=_TAB_SELECTED),
                dcc.Tab(label="Lettres de motivation", value="tab-letters",
                        style=_TAB_STYLE, selected_style=_TAB_SELECTED),
            ],
            style={"borderBottom": "1px solid #3a362f"},
        ),
        html.Div(id="tab-content", className="mt-3"),
        all_modals(),
    ],
)


@app.callback(
    dash.Output("tab-content", "children"),
    dash.Input("main-tabs", "value"),
)
def _render_tab(active_tab):
    """Monte le contenu de l'onglet actif (dcc.Tabs ne rend que l'onglet courant)."""
    if active_tab == "tab-letters":
        return letters_layout()
    return home_layout()


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
