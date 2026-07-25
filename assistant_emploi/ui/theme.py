"""Palette et helpers visuels — thème sombre anthracite / ambre."""
from __future__ import annotations

# Palette principale (thème sombre anthracite / ambre)
BG = "#1a1815"          # fond général
BG_SIDEBAR = "#1e1c18"  # fond de la barre latérale
BG_ELEV = "#232019"     # surfaces surélevées (cartes)
BG_ELEV_2 = "#2b2721"   # surfaces secondaires (bulles, hover)
BORDER = "#322d25"
BORDER_SOFT = "#3a352c" # bordures pointillées / champs
TEXT = "#f1ece3"
TEXT_MUTED = "#a89f8f"
TEXT_DIM = "#756c5f"    # texte très discret
ACCENT = "#dd9a4e"      # ambre
ACCENT_HOVER = "#e8ac66"
GREEN = "#6fae6f"
RED = "#d16c5c"
BLUE = "#5f93d1"
YELLOW = "#dcbb4f"
PURPLE = "#c48ad9"

# Couleurs associées aux statuts connus (repli sur ACCENT).
STATUS_COLORS = {
    "Candidature envoyée": BLUE,
    "Refus": RED,
    "1er entretien": YELLOW,
    "2ème entretien (technique)": PURPLE,
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

# Statuts considérés comme « réponses négatives » pour le suivi par CV.
NEGATIVE_STATUSES = {"Refus"}

# Séquence de couleurs pour les graphes catégoriels.
CATEGORICAL = [ACCENT, BLUE, GREEN, YELLOW, RED, PURPLE, "#7ec8c0", TEXT_MUTED]

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
