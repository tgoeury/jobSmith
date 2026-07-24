"""Onglet Accueil : CV actuel, statistiques et liste des candidatures."""
from __future__ import annotations

from datetime import date, datetime

import dash_bootstrap_components as dbc
from dash import dcc, html

from .. import repository as repo
from ..config import CONFIG
from . import theme


# ---------------------------------------------------------------------------
# Helpers de formatage
# ---------------------------------------------------------------------------

def _fmt_date(value) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    return str(value or "")


def _fmt_datetime(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value or "")


# ---------------------------------------------------------------------------
# Rendu d'une candidature
# ---------------------------------------------------------------------------

def _status_badge(label: str | None) -> html.Span:
    color = theme.status_color(label)
    return html.Span(
        label or "—",
        className="status-badge",
        style={"backgroundColor": color},
    )


def _cv_label(cv_name: str | None) -> html.Span:
    """Étiquette du CV ; « CV inconnu » (en évidence) si aucun CV valide n'est attaché."""
    if cv_name:
        return html.Span(f"CV : {cv_name}")
    return html.Span("CV inconnu", className="cv-unknown",
                     style={"color": theme.RED, "fontWeight": 600})


def _annonce_link(app: dict) -> html.Span:
    status = app["annonce_status"]
    if status == "ok":
        return html.A(
            "📄 Voir l'annonce (copie locale)",
            href=f"/annonce/{app['id']}",
            target="_blank",
        )
    if status == "failed":
        return html.Span(
            [
                html.Span("Copie locale indisponible ", className="annonce-na"),
                html.A("· annonce d'origine", href=app["url"], target="_blank")
                if app["url"]
                else "",
            ]
        )
    # 'na' : moyen de candidater, pas une URL téléchargeable.
    if app["url"]:
        if app["url"].lower().startswith("http"):
            return html.A("Annonce d'origine", href=app["url"], target="_blank")
        return html.Span(f"Moyen : {app['url']}", className="annonce-na")
    return html.Span("Pas d'annonce", className="annonce-na")


def _comment_bubble(comment: dict) -> html.Div:
    created, updated = comment["created_at"], comment["updated_at"]
    # Tolérance : created_at/updated_at diffèrent de quelques µs à la création.
    edited = bool(
        updated
        and isinstance(updated, datetime)
        and isinstance(created, datetime)
        and (updated - created).total_seconds() > 2
    )
    time_label = _fmt_datetime(created)
    if edited:
        time_label += f" · modifié {_fmt_datetime(updated)}"
    return html.Div(
        className="comment-bubble",
        children=[
            html.Button(
                "✎",
                className="comment-edit-btn",
                id={"type": "edit-comment", "index": comment["id"]},
                n_clicks=0,
                title="Modifier",
            ),
            html.Div(comment["content"], className="comment-text"),
            html.Div(time_label, className="comment-time"),
        ],
    )


def _status_history(history: list[dict]) -> html.Ul:
    items = []
    for event in history:
        color = theme.status_color(event["label"])
        line = f"{event['label']} — {_fmt_date(event['changed_at'])}"
        if event.get("note"):
            line += f" ({event['note']})"
        items.append(
            html.Li([html.Span(className="dot", style={"backgroundColor": color}), line])
        )
    return html.Ul(items, className="status-history")


def build_application_card(app: dict) -> dbc.Card:
    idx = app["id"]
    comments = app["comments"]

    return dbc.Card(
        className="candidature-card",
        children=dbc.CardBody(
            [
                html.Div(
                    className="d-flex justify-content-between align-items-start",
                    children=[
                        html.Div(
                            [
                                html.Div(app["title"], className="cand-title"),
                                html.Div(
                                    app["company"] or "—", className="cand-company"
                                ),
                            ]
                        ),
                        _status_badge(app["current_status"]),
                    ],
                ),
                html.Div(
                    className="cand-meta mt-1",
                    children=[
                        html.Span(f"🗓️ {_fmt_date(app['applied_at'])}"),
                        html.Span("  •  "),
                        _cv_label(app["cv_name"]),
                        html.Span("  •  "),
                        _annonce_link(app),
                    ],
                ),
                _status_history(app["history"]),
                # Fil de commentaires
                html.Div(
                    [_comment_bubble(c) for c in comments],
                    className="comments-thread",
                )
                if comments
                else html.Div(),
                dbc.InputGroup(
                    class_name="mt-2",
                    size="sm",
                    children=[
                        dbc.Input(
                            id={"type": "new-comment-input", "index": idx},
                            placeholder="Ajouter un commentaire…",
                        ),
                        dbc.Button(
                            "Envoyer",
                            id={"type": "new-comment-btn", "index": idx},
                            className="btn-outline-accent",
                            n_clicks=0,
                        ),
                    ],
                ),
                # Actions
                html.Div(
                    className="cand-actions mt-2 text-end",
                    children=[
                        dbc.Button(
                            "Changer le statut",
                            id={"type": "status-app", "index": idx},
                            size="sm",
                            className="btn-ghost",
                            n_clicks=0,
                        ),
                        dbc.Button(
                            "Éditer",
                            id={"type": "edit-app", "index": idx},
                            size="sm",
                            className="btn-outline-accent",
                            n_clicks=0,
                        ),
                    ],
                ),
            ]
        ),
    )


# ---------------------------------------------------------------------------
# Section CV
# ---------------------------------------------------------------------------

def build_cv_section() -> dbc.Card:
    current = repo.get_current_cv()
    others = [cv for cv in repo.list_cvs() if not cv["is_current"]]

    if current:
        current_block = html.Div(
            [
                html.Div(
                    [
                        html.Span(current["name"], className="cv-title"),
                        html.Span(" "),
                        dbc.Badge("CV actuel", className="cv-current-badge ms-2"),
                    ]
                ),
                html.Div(
                    f"Chargé le {_fmt_datetime(current['uploaded_at'])}",
                    className="muted",
                    style={"fontSize": "0.82rem"},
                ),
                html.A(
                    "⬇ Télécharger",
                    href=f"/cv/{current['id']}",
                    target="_blank",
                    className="d-inline-block mt-1",
                ),
            ]
        )
    else:
        current_block = dbc.Alert(
            [
                html.Strong("⚠️ Aucun CV enregistré. "),
                "Chargez un CV pour l'associer à vos candidatures ; "
                "sans cela, elles seront marquées « CV inconnu ».",
            ],
            color="warning",
            className="mb-0",
            id="no-cv-alert",
        )

    versions_block = html.Div()
    if others:
        versions_block = html.Details(
            className="mt-2",
            children=[
                html.Summary(
                    f"Anciennes versions ({len(others)})",
                    style={"cursor": "pointer", "color": "var(--text-muted)"},
                ),
                html.Ul(
                    [
                        html.Li(
                            [
                                html.A(cv["name"], href=f"/cv/{cv['id']}", target="_blank"),
                                html.Span(
                                    f" — {_fmt_datetime(cv['uploaded_at'])}",
                                    className="muted",
                                ),
                            ]
                        )
                        for cv in others
                    ],
                    style={"marginTop": "0.4rem"},
                ),
            ],
        )

    return dbc.Card(
        className="cv-card mb-3",
        children=dbc.CardBody(
            [
                html.Div(
                    className="d-flex justify-content-between align-items-start",
                    children=[
                        current_block,
                        dbc.Button(
                            "Charger un nouveau CV",
                            id="btn-upload-cv",
                            className="btn-outline-accent",
                            n_clicks=0,
                        ),
                    ],
                ),
                versions_block,
            ]
        ),
    )


# ---------------------------------------------------------------------------
# Section statistiques
# ---------------------------------------------------------------------------

def _tile(value, label, tone: str = "") -> html.Div:
    value_class = "stat-value" + (f" {tone}" if tone else "")
    return html.Div(
        className="stat-tile",
        children=[
            html.Div(str(value), className=value_class),
            html.Div(label, className="stat-label"),
        ],
    )


def build_stat_tiles() -> html.Div:
    """Rangée des 4 indicateurs clés (partagée par le tableau de bord et les stats)."""
    from .. import stats as stats_mod

    nums = stats_mod.summary_numbers()
    return html.Div(
        className="stat-tiles",
        children=[
            _tile(nums["total"], "Candidatures"),
            _tile(nums["last_30"], "30 derniers jours"),
            _tile(nums["positives"], "Réponses positives", tone="green"),
            _tile(nums["refus"], "Refus", tone="red"),
        ],
    )


def _chart_card(title: str, figure) -> html.Div:
    return html.Div(
        className="chart-card",
        children=[
            html.Div(title, className="chart-title"),
            dcc.Graph(figure=figure, config={"displayModeBar": False}),
        ],
    )


def build_stats_section():
    """Contenu de la page Statistiques : tuiles + graphiques Plotly."""
    from .. import stats as stats_mod

    return html.Div(
        [
            build_stat_tiles(),
            dbc.Row(
                [
                    dbc.Col(_chart_card("Répartition par statut",
                                        stats_mod.figure_global_status()), md=6),
                    dbc.Col(_chart_card("30 derniers jours",
                                        stats_mod.figure_last_30_days()), md=6),
                ],
                class_name="g-3",
            ),
            _chart_card("Candidatures par CV", stats_mod.figure_by_cv()),
        ]
    )


# ---------------------------------------------------------------------------
# Liste des candidatures
# ---------------------------------------------------------------------------

def render_application_cards(apps: list[dict]) -> html.Div:
    if not apps:
        return html.Div(
            "Aucune candidature ne correspond.", className="empty-state"
        )
    return html.Div(
        [build_application_card(app) for app in apps], className="apps-stack"
    )


def _recent_row(app: dict) -> html.Div:
    """Ligne compacte pour la liste « candidatures récentes » du tableau de bord."""
    return html.Div(
        className="recent-row",
        children=[
            html.Div(
                [
                    html.Div(app["title"], className="recent-title"),
                    html.Div(
                        f"{app['company'] or '—'} · {_fmt_date(app['applied_at'])}",
                        className="recent-sub",
                    ),
                ]
            ),
            _status_badge(app["current_status"]),
        ],
    )


def build_dashboard_body() -> html.Div:
    """Tuiles + candidatures récentes (partie du tableau de bord rafraîchie en direct)."""
    recents = recent_applications()[:4]
    if recents:
        recent_block = html.Div([_recent_row(a) for a in recents])
    else:
        recent_block = html.Div(
            "Aucune candidature pour le moment.", className="empty-state"
        )
    return html.Div(
        [
            build_stat_tiles(),
            html.Div(
                className="section-heading",
                children=[
                    html.Div("Candidatures récentes", className="title"),
                    html.Span("Voir tout →", id="dash-see-all", n_clicks=0,
                              className="link-accent"),
                ],
            ),
            recent_block,
        ]
    )


def recent_applications() -> list[dict]:
    return repo.list_recent_applications(CONFIG.get("home_recent_count", 10))


def _status_filter_options() -> list[dict]:
    options = [{"label": "Tous les statuts", "value": ""}]
    options += [{"label": s["label"], "value": s["label"]}
                for s in repo.list_status_types()]
    return options


def build_filter_bar() -> dbc.Card:
    """Barre de recherche / filtres au-dessus de la liste des candidatures."""
    return dbc.Card(
        className="mb-3",
        children=dbc.CardBody(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [dbc.Label("Intitulé du poste"),
                             dbc.Input(id="filter-title", type="text",
                                       placeholder="ex. Data Scientist", debounce=True)],
                            md=3,
                        ),
                        dbc.Col(
                            [dbc.Label("Entreprise"),
                             dbc.Input(id="filter-company", type="text",
                                       placeholder="ex. ACME", debounce=True)],
                            md=3,
                        ),
                        dbc.Col(
                            [dbc.Label("Statut"),
                             dbc.Select(id="filter-status",
                                        options=_status_filter_options(), value="")],
                            md=2,
                        ),
                        dbc.Col(
                            [dbc.Label("Du"),
                             dbc.Input(id="filter-date-from", type="date")],
                            md=2,
                        ),
                        dbc.Col(
                            [dbc.Label("Au"),
                             dbc.Input(id="filter-date-to", type="date")],
                            md=2,
                        ),
                    ],
                    class_name="g-2",
                ),
                html.Div(
                    className="d-flex gap-2 mt-3 align-items-center",
                    children=[
                        dbc.Button("🔍 Rechercher", id="btn-search",
                                   className="btn-accent", n_clicks=0),
                        dbc.Button("Réinitialiser", id="btn-reset-search",
                                   className="btn-ghost", n_clicks=0),
                    ],
                ),
            ]
        ),
    )


# ---------------------------------------------------------------------------
# Layout de l'onglet
# ---------------------------------------------------------------------------

_WEEKDAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
    "août", "septembre", "octobre", "novembre", "décembre",
]


def _french_long_date(d: date) -> str:
    label = f"{_WEEKDAYS[d.weekday()]} {d.day} {_MONTHS[d.month - 1]} {d.year}"
    return label[0].upper() + label[1:]


def _page_header(title: str, subtitle: str | None, new_btn_id: str) -> html.Div:
    left = [html.H1(title, className="page-title")]
    if subtitle:
        left.append(html.Div(subtitle, className="page-subtitle"))
    return html.Div(
        className="page-header",
        children=[
            html.Div(left),
            dbc.Button("＋ Nouvelle candidature", id=new_btn_id,
                       className="btn-accent", n_clicks=0),
        ],
    )


def dashboard_layout() -> html.Div:
    """Page « Tableau de bord » : CV actuel, indicateurs et candidatures récentes."""
    return html.Div(
        [
            _page_header("Tableau de bord", _french_long_date(date.today()),
                         "btn-new-app-dash"),
            html.Div(build_cv_section(), id="cv-section"),
            html.Div(build_dashboard_body(), id="dashboard-body"),
        ]
    )


def candidatures_layout() -> html.Div:
    """Page « Candidatures » : filtres + liste complète."""
    return html.Div(
        [
            _page_header("Candidatures", None, "btn-new-app"),
            html.Div(
                className="d-flex gap-2 flex-wrap mb-3",
                children=[
                    dbc.Button("⬇ Exporter (.ods)", id="btn-export-ods",
                               className="btn-ghost", n_clicks=0),
                    dbc.Button("↻ Réessayer les copies manquantes",
                               id="btn-retry-annonces", className="btn-ghost",
                               n_clicks=0),
                ],
            ),
            html.Div(id="action-feedback", className="mb-2"),
            # État des filtres actifs (réinitialisé au montage de la page).
            dcc.Store(id="active-filters", data=None),
            build_filter_bar(),
            html.Div(
                className="section-heading",
                children=[
                    html.Span(
                        f"{CONFIG.get('home_recent_count', 10)} plus récentes",
                        id="search-summary", className="muted",
                    ),
                ],
            ),
            dcc.Loading(
                html.Div(render_application_cards(recent_applications()),
                         id="apps-list"),
                type="default",
            ),
            dcc.Download(id="download-ods"),
        ]
    )


def stats_layout() -> html.Div:
    """Page « Statistiques »."""
    return html.Div(
        [
            html.H1("Statistiques", className="page-title",
                    style={"marginBottom": "26px"}),
            html.Div(build_stats_section(), id="stats-section"),
        ]
    )
