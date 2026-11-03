"""Définition des fenêtres modales (candidature, CV, statut, commentaire)."""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..models import APPLICATION_KINDS, DEFAULT_KIND


def application_modal() -> dbc.Modal:
    """Modale partagée : nouvelle candidature ET édition."""
    return dbc.Modal(
        id="app-modal",
        size="lg",
        is_open=False,
        children=[
            dbc.ModalHeader(dbc.ModalTitle(id="app-modal-title")),
            dbc.ModalBody(
                [
                    dbc.Label("Type"),
                    dbc.RadioItems(
                        id="app-input-kind",
                        options=[{"label": label, "value": key}
                                 for key, label in APPLICATION_KINDS.items()],
                        value=DEFAULT_KIND,
                        inline=True,
                        class_name="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Date de candidature",
                                              id="app-label-date"),
                                    dbc.Input(id="app-input-date", type="date"),
                                ],
                                md=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("CV utilisé"),
                                    dbc.Select(id="app-select-cv"),
                                ],
                                md=6,
                            ),
                        ],
                        class_name="mb-3",
                    ),
                    dbc.Label("Intitulé du poste *", id="app-label-title"),
                    dbc.Input(id="app-input-title", type="text",
                              placeholder="Data Scientist (H/F)", class_name="mb-3"),
                    dbc.Label("Entreprise"),
                    dbc.Input(id="app-input-company", type="text",
                              placeholder="Nom de l'entreprise", class_name="mb-3"),
                    dbc.Label("Contact"),
                    dbc.Input(id="app-input-contact", type="text",
                              placeholder="Nom, cabinet, téléphone, e-mail…",
                              class_name="mb-3"),
                    dbc.Label("URL de l'annonce ou moyen de candidater"),
                    dbc.Textarea(
                        id="app-input-url",
                        placeholder="https://…  ou  « Candidatures FT »",
                        style={"height": "60px"},
                        class_name="mb-2",
                    ),
                    html.Div(
                        "Si une URL http(s) est fournie, une copie locale de l'annonce "
                        "sera téléchargée après l'enregistrement.",
                        className="muted",
                        style={"fontSize": "0.8rem"},
                    ),
                    html.Details(
                        className="mt-3",
                        children=[
                            html.Summary(
                                "Coller le texte de l'annonce (si la copie automatique "
                                "échoue)",
                                className="muted",
                                style={"cursor": "pointer", "fontSize": "0.85rem"},
                            ),
                            dbc.Textarea(
                                id="app-input-annonce-text",
                                placeholder="Texte de l'annonce ou du mail reçu. "
                                            "Remplace la copie locale actuelle.",
                                style={"height": "140px"},
                                class_name="mt-2",
                            ),
                        ],
                    ),
                    html.Div(id="app-modal-feedback", className="mt-2"),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Annuler", id="app-modal-cancel", className="btn-ghost"),
                    dbc.Button("Enregistrer", id="app-modal-save", className="btn-accent"),
                ]
            ),
        ],
    )


def cv_modal() -> dbc.Modal:
    return dbc.Modal(
        id="cv-modal",
        is_open=False,
        children=[
            dbc.ModalHeader(dbc.ModalTitle("Charger un nouveau CV")),
            dbc.ModalBody(
                [
                    dbc.Label("Nom du CV *"),
                    dbc.Input(id="cv-input-name", type="text",
                              placeholder="CV_Data_Scientist_v2", class_name="mb-3"),
                    dcc.Upload(
                        id="cv-upload",
                        children=html.Div(
                            ["Glisser-déposer ou ", html.A("choisir un fichier")]
                        ),
                        style={
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "8px",
                            "padding": "1.2rem",
                            "textAlign": "center",
                        },
                        multiple=False,
                    ),
                    html.Div(id="cv-upload-status", className="mt-2 muted"),
                    html.Div(id="cv-modal-feedback", className="mt-2"),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Annuler", id="cv-modal-cancel", className="btn-ghost"),
                    dbc.Button("Enregistrer comme CV actuel", id="cv-modal-save",
                               className="btn-accent"),
                ]
            ),
        ],
    )


def status_modal() -> dbc.Modal:
    return dbc.Modal(
        id="status-modal",
        is_open=False,
        children=[
            dbc.ModalHeader(dbc.ModalTitle("Changer le statut", id="status-modal-title")),
            dbc.ModalBody(
                [
                    html.Div(id="status-modal-app-label", className="muted mb-2"),
                    dbc.Label("Nouveau statut", id="status-select-label"),
                    dbc.Select(id="status-select", class_name="mb-3"),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Date du changement"),
                                    dbc.Input(id="status-date", type="date"),
                                ],
                                md=6,
                            ),
                        ],
                        class_name="mb-3",
                    ),
                    dbc.Label("Note (optionnelle)"),
                    dbc.Textarea(id="status-note", style={"height": "60px"},
                                 class_name="mb-3"),
                    html.Hr(),
                    dbc.Label("Ajouter un nouveau type de statut"),
                    dbc.InputGroup(
                        [
                            dbc.Input(id="new-status-input", type="text",
                                      placeholder="ex. 1er entretien"),
                            dbc.Button("Ajouter", id="add-status-btn",
                                       className="btn-outline-accent"),
                        ],
                        class_name="mb-2",
                    ),
                    html.Div(id="status-modal-feedback"),
                ]
            ),
            dbc.ModalFooter(
                [
                    # Visible uniquement en édition d'une étape existante.
                    dbc.Button("Supprimer l'étape", id="status-modal-delete",
                               className="btn-ghost", style={"display": "none"}),
                    dbc.Button("Annuler", id="status-modal-cancel", className="btn-ghost"),
                    dbc.Button("Enregistrer le statut", id="status-modal-save",
                               className="btn-accent"),
                ]
            ),
        ],
    )


def comment_modal() -> dbc.Modal:
    return dbc.Modal(
        id="comment-modal",
        is_open=False,
        children=[
            dbc.ModalHeader(dbc.ModalTitle("Modifier le commentaire")),
            dbc.ModalBody(
                [
                    dbc.Textarea(id="comment-modal-textarea",
                                 style={"height": "200px"}),
                    html.Div(id="comment-modal-feedback", className="mt-2"),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Supprimer", id="comment-modal-delete",
                               className="btn-ghost", style={"color": "var(--red)"}),
                    dbc.Button("Annuler", id="comment-modal-cancel", className="btn-ghost"),
                    dbc.Button("Enregistrer", id="comment-modal-save",
                               className="btn-accent"),
                ]
            ),
        ],
    )


def all_modals() -> html.Div:
    return html.Div(
        [
            application_modal(),
            cv_modal(),
            status_modal(),
            comment_modal(),
        ]
    )
