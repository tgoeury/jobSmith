"""Onglet Lettres de motivation : liste + éditeur."""
from __future__ import annotations

from datetime import date, datetime

import dash_bootstrap_components as dbc
from dash import dcc, html

from .. import repository as repo


def _fmt_datetime(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value or "")


def build_letters_list(selected_id: int | None = None) -> html.Div:
    letters = repo.list_cover_letters()
    if not letters:
        return html.Div("Aucune lettre pour le moment.", className="muted")
    items = []
    for letter in letters:
        active = " active-letter" if letter["id"] == selected_id else ""
        items.append(
            html.Div(
                className=f"letter-item mb-2{active}",
                id={"type": "letter-item", "index": letter["id"]},
                n_clicks=0,
                children=[
                    html.Div(letter["name"], style={"fontWeight": 600}),
                    html.Div(
                        f"{letter['char_count']} caractères · "
                        f"{_fmt_datetime(letter['updated_at'])}",
                        className="letter-meta",
                    ),
                ],
            )
        )
    return html.Div(items)


def letters_layout() -> html.Div:
    return html.Div(
        [
            html.H1("Lettres de motivation", className="page-title",
                    style={"marginBottom": "24px"}),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button("＋ Nouvelle lettre", id="btn-new-letter",
                                       className="btn-accent mb-3 w-100", n_clicks=0),
                            html.Div(build_letters_list(None), id="letters-list"),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Input(id="letter-name", type="text",
                                      placeholder="Nom de la lettre", class_name="mb-2"),
                            dbc.Textarea(
                                id="letter-content",
                                placeholder="Rédigez votre lettre de motivation type…",
                                style={"height": "420px"},
                                class_name="mb-2",
                            ),
                            html.Div(
                                className="d-flex justify-content-between align-items-center",
                                children=[
                                    html.Span(id="letter-charcount", className="muted"),
                                    html.Div(
                                        [
                                            dbc.Button("Supprimer", id="letter-delete",
                                                       className="btn-ghost me-2",
                                                       n_clicks=0,
                                                       style={"color": "var(--red)"}),
                                            dbc.Button("Enregistrer", id="letter-save",
                                                       className="btn-accent", n_clicks=0),
                                        ]
                                    ),
                                ],
                            ),
                            html.Div(id="letter-feedback", className="mt-2"),
                        ],
                        md=8,
                    ),
                ]
            ),
        ]
    )
