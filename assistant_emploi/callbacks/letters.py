"""Callbacks des lettres de motivation."""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, no_update
from dash.exceptions import PreventUpdate

from .. import repository as repo
from ..ui.letters import build_letters_list


def _clicked() -> bool:
    return bool(ctx.triggered and ctx.triggered[0]["value"])


@callback(
    Output("letters-list", "children"),
    Input("refresh-letters", "data"),
    State("selected-letter-id", "data"),
    prevent_initial_call=True,
)
def _render_letters(_refresh, selected):
    return build_letters_list(selected)


@callback(
    Output("letter-charcount", "children"),
    Input("letter-content", "value"),
)
def _charcount(content):
    return f"{len(content or '')} caractères"


@callback(
    Output("selected-letter-id", "data"),
    Output("letter-name", "value"),
    Output("letter-content", "value"),
    Output("letters-list", "children", allow_duplicate=True),
    Input("btn-new-letter", "n_clicks"),
    prevent_initial_call=True,
)
def _new_letter(_n):
    return None, "", "", build_letters_list(None)


@callback(
    Output("selected-letter-id", "data", allow_duplicate=True),
    Output("letter-name", "value", allow_duplicate=True),
    Output("letter-content", "value", allow_duplicate=True),
    Output("letters-list", "children", allow_duplicate=True),
    Input({"type": "letter-item", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def _select_letter(_clicks):
    if not _clicked():
        raise PreventUpdate
    letter_id = ctx.triggered_id["index"]
    letter = repo.get_cover_letter(letter_id)
    if not letter:
        raise PreventUpdate
    return (
        letter_id,
        letter["name"],
        letter["content"],
        build_letters_list(letter_id),
    )


@callback(
    Output("selected-letter-id", "data", allow_duplicate=True),
    Output("refresh-letters", "data", allow_duplicate=True),
    Output("letter-feedback", "children"),
    Output("letters-list", "children", allow_duplicate=True),
    Input("letter-save", "n_clicks"),
    State("selected-letter-id", "data"),
    State("letter-name", "value"),
    State("letter-content", "value"),
    State("refresh-letters", "data"),
    prevent_initial_call=True,
)
def _save_letter(_n, letter_id, name, content, refresh):
    name = (name or "").strip()
    if not name:
        return (
            no_update,
            no_update,
            dbc.Alert("Le nom de la lettre est obligatoire.", color="danger",
                      class_name="py-2 mb-0"),
            no_update,
        )
    content = content or ""
    if letter_id:
        repo.update_cover_letter(letter_id, name, content)
        new_id = letter_id
    else:
        new_id = repo.create_cover_letter(name, content)
    feedback = dbc.Alert(
        f"Lettre enregistrée ({len(content)} caractères).", color="success",
        class_name="py-2 mb-0", duration=3000,
    )
    return new_id, (refresh or 0) + 1, feedback, build_letters_list(new_id)


@callback(
    Output("selected-letter-id", "data", allow_duplicate=True),
    Output("letter-name", "value", allow_duplicate=True),
    Output("letter-content", "value", allow_duplicate=True),
    Output("refresh-letters", "data", allow_duplicate=True),
    Output("letters-list", "children", allow_duplicate=True),
    Input("letter-delete", "n_clicks"),
    State("selected-letter-id", "data"),
    State("refresh-letters", "data"),
    prevent_initial_call=True,
)
def _delete_letter(_n, letter_id, refresh):
    if not letter_id:
        raise PreventUpdate
    repo.delete_cover_letter(letter_id)
    return None, "", "", (refresh or 0) + 1, build_letters_list(None)
