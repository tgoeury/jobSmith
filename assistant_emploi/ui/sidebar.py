"""Barre latérale de navigation (logo + liens vers les 4 pages)."""
from __future__ import annotations

from urllib.parse import quote

from dash import html

from ..config import CONFIG

# Icônes SVG reprises de la maquette. Dash n'a pas de balise <svg> native : on les
# applique en `mask-image` sur un <span> dont la couleur suit `currentColor`, ce qui
# permet à l'icône de se teinter comme le texte (muted / ambre à l'état actif).
_ICONS_SVG = {
    "dashboard": (
        "<svg xmlns='http://www.w3.org/2000/svg' width='17' height='17' viewBox='0 0 17 17'>"
        "<rect x='0' y='0' width='7' height='7' rx='1.5'/>"
        "<rect x='10' y='0' width='7' height='7' rx='1.5' opacity='0.55'/>"
        "<rect x='0' y='10' width='7' height='7' rx='1.5' opacity='0.55'/>"
        "<rect x='10' y='10' width='7' height='7' rx='1.5'/></svg>"
    ),
    "candidatures": (
        "<svg xmlns='http://www.w3.org/2000/svg' width='17' height='17' viewBox='0 0 17 17'>"
        "<rect x='2' y='1' width='13' height='15' rx='1.5' fill='none' stroke='#000' stroke-width='1.4'/>"
        "<line x1='5' y1='5.5' x2='12' y2='5.5' stroke='#000' stroke-width='1.4'/>"
        "<line x1='5' y1='9' x2='12' y2='9' stroke='#000' stroke-width='1.4'/>"
        "<line x1='5' y1='12.5' x2='9.5' y2='12.5' stroke='#000' stroke-width='1.4'/></svg>"
    ),
    "stats": (
        "<svg xmlns='http://www.w3.org/2000/svg' width='17' height='17' viewBox='0 0 17 17'>"
        "<rect x='1' y='9' width='3.4' height='7' rx='1'/>"
        "<rect x='6.8' y='4' width='3.4' height='12' rx='1'/>"
        "<rect x='12.6' y='1' width='3.4' height='15' rx='1' opacity='0.65'/></svg>"
    ),
    "letters": (
        "<svg xmlns='http://www.w3.org/2000/svg' width='17' height='17' viewBox='0 0 17 17'>"
        "<rect x='1' y='2.5' width='15' height='12' rx='1.5' fill='none' stroke='#000' stroke-width='1.4'/>"
        "<path d='M1.5 3.5L8.5 9.5L15.5 3.5' fill='none' stroke='#000' stroke-width='1.4'/></svg>"
    ),
}

_NAV = [
    ("dashboard", "Tableau de bord"),
    ("candidatures", "Candidatures"),
    ("stats", "Statistiques"),
    ("letters", "Lettres de motivation"),
]


def _icon(page: str) -> html.Span:
    mask = f"url(\"data:image/svg+xml,{quote(_ICONS_SVG[page])}\") center/contain no-repeat"
    return html.Span(
        style={
            "width": "17px",
            "height": "17px",
            "flex": "none",
            "display": "inline-block",
            "backgroundColor": "currentColor",
            "WebkitMask": mask,
            "mask": mask,
        }
    )


def _nav_item(page: str, label: str, active: str) -> html.Div:
    className = "nav-item active" if page == active else "nav-item"
    return html.Div(
        id=f"nav-{page}",
        className=className,
        n_clicks=0,
        children=[_icon(page), html.Span(label)],
    )


def sidebar(active: str = "dashboard") -> html.Div:
    return html.Div(
        className="sidebar",
        children=[
            html.Div(
                className="sidebar-brand",
                children=[
                    html.Div(className="brand-logo"),
                    html.Div(CONFIG.get("app_title", "Assistant Emploi"),
                             className="brand-name"),
                ],
            ),
            html.Div(
                className="sidebar-nav",
                children=[
                    html.Div("Navigation", className="nav-heading"),
                    *[_nav_item(page, label, active) for page, label in _NAV],
                ],
            ),
            html.Div(
                "Données locales · aucune synchronisation",
                className="sidebar-footer",
            ),
        ],
    )
