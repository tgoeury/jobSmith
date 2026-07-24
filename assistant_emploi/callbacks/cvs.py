"""Callbacks de gestion des CV (upload d'une nouvelle version)."""
from __future__ import annotations

import base64
import binascii
import uuid
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, no_update
from dash.exceptions import PreventUpdate

from .. import repository as repo
from ..config import CV_DIR


@callback(
    Output("cv-modal", "is_open"),
    Output("cv-input-name", "value"),
    Output("cv-upload", "contents"),
    Output("cv-upload-status", "children"),
    Output("cv-modal-feedback", "children"),
    Input("btn-upload-cv", "n_clicks"),
    prevent_initial_call=True,
)
def _open_cv_modal(n_clicks):
    # `btn-upload-cv` est rendu dynamiquement (section CV) : ignorer l'apparition
    # initiale du composant (n_clicks=0) pour ne pas ouvrir la modale au chargement.
    if not n_clicks:
        raise PreventUpdate
    return True, "", None, "", ""


@callback(
    Output("cv-modal", "is_open", allow_duplicate=True),
    Input("cv-modal-cancel", "n_clicks"),
    prevent_initial_call=True,
)
def _cancel_cv_modal(_n):
    return False


@callback(
    Output("cv-upload-status", "children", allow_duplicate=True),
    Input("cv-upload", "filename"),
    prevent_initial_call=True,
)
def _show_filename(filename):
    if not filename:
        return ""
    return f"Fichier sélectionné : {filename}"


@callback(
    Output("cv-modal", "is_open", allow_duplicate=True),
    Output("refresh-apps", "data", allow_duplicate=True),
    Output("cv-modal-feedback", "children", allow_duplicate=True),
    Input("cv-modal-save", "n_clicks"),
    State("cv-input-name", "value"),
    State("cv-upload", "contents"),
    State("cv-upload", "filename"),
    State("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _save_cv(_n, name, contents, filename, refresh):
    name = (name or "").strip()
    if not name:
        return no_update, no_update, dbc.Alert(
            "Le nom du CV est obligatoire.", color="danger", class_name="py-2 mb-0"
        )
    if not contents:
        return no_update, no_update, dbc.Alert(
            "Veuillez sélectionner un fichier.", color="danger", class_name="py-2 mb-0"
        )

    # contents = "data:<mime>;base64,<...>"
    try:
        _header, b64 = contents.split(",", 1)
        raw = base64.b64decode(b64)
    except (ValueError, binascii.Error):
        return no_update, no_update, dbc.Alert(
            "Fichier illisible.", color="danger", class_name="py-2 mb-0"
        )

    suffix = Path(filename or "cv.pdf").suffix or ".pdf"
    stored = f"{uuid.uuid4().hex}{suffix}"
    (CV_DIR / stored).write_bytes(raw)

    repo.create_cv(
        name=name,
        stored_filename=stored,
        original_filename=filename or stored,
        make_current=True,
    )
    return False, (refresh or 0) + 1, ""
