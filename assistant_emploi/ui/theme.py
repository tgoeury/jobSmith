"""Palette et helpers visuels — thème sombre anthracite / ambre."""
from __future__ import annotations

# Palette principale
BG = "#1c1b19"          # fond général
BG_ELEV = "#26241f"     # surfaces surélevées (cartes)
BG_ELEV_2 = "#302d27"   # surfaces secondaires
BORDER = "#3a362f"
TEXT = "#eae6df"
TEXT_MUTED = "#a49e92"
ACCENT = "#d9843a"      # ambre
ACCENT_HOVER = "#e6975a"
GREEN = "#6fae6f"
RED = "#cf6b5c"
BLUE = "#5c8fcf"
YELLOW = "#d9b84a"

# Couleurs associées aux statuts connus (repli sur ACCENT).
STATUS_COLORS = {
    "Candidature envoyée": BLUE,
    "Refus": RED,
    "1er entretien": YELLOW,
    "2ème entretien (technique)": "#c58bd9",
    "Entretien": YELLOW,
    "Offre": GREEN,
    "Accepté": GREEN,
    "Inconnu": TEXT_MUTED,
}

# Statuts considérés comme « réponses positives » pour le suivi par CV.
POSITIVE_STATUSES = {
    "1er entretien",
    "2ème entretien (technique)",
    "Entretien",
    "Offre",
    "Accepté",
}

# Séquence de couleurs pour les graphes catégoriels.
CATEGORICAL = [ACCENT, BLUE, GREEN, YELLOW, RED, "#c58bd9", "#7ec8c0", TEXT_MUTED]

# Mise en forme commune des figures Plotly.
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, family="system-ui, -apple-system, Segoe UI, sans-serif"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    colorway=CATEGORICAL,
)


def status_color(label: str | None) -> str:
    return STATUS_COLORS.get(label or "Inconnu", ACCENT)
