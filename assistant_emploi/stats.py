"""Rapport statistique : figures Plotly (global, par CV, 30 derniers jours)."""
from __future__ import annotations

import plotly.graph_objects as go

from .repository import stats_by_current_status, stats_by_cv, stats_last_30_days
from .ui.theme import (
    GREEN,
    NEGATIVE_STATUSES,
    PLOTLY_LAYOUT,
    POSITIVE_STATUSES,
    RED,
    TEXT_MUTED,
    status_color,
)


def _empty_fig(message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.add_annotation(
        text=message, showarrow=False, font=dict(color=TEXT_MUTED, size=14)
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def figure_global_status() -> go.Figure:
    """Répartition de toutes les candidatures par statut courant (barres)."""
    counts = stats_by_current_status()
    if not counts:
        return _empty_fig("Aucune candidature")
    labels = list(counts.keys())
    values = [counts[label] for label in labels]
    colors = [status_color(label) for label in labels]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors))
    fig.update_layout(
        title=f"Répartition par statut — {sum(values)} candidature(s)",
        **PLOTLY_LAYOUT,
    )
    return fig


def figure_by_cv() -> go.Figure:
    """Par CV : une barre par CV, % réponses positives empilé au-dessus des % négatives."""
    data = stats_by_cv()
    if not data:
        return _empty_fig("Aucune candidature")
    data = sorted(data, key=lambda d: d["total"], reverse=True)
    names = [f"{d['cv_name']} (n={d['total']})" for d in data]

    def _pct(entry: dict, statuses: set[str]) -> float:
        count = sum(cnt for lbl, cnt in entry["statuses"].items() if lbl in statuses)
        return count / entry["total"] * 100 if entry["total"] else 0

    negatives = [_pct(d, NEGATIVE_STATUSES) for d in data]
    positives = [_pct(d, POSITIVE_STATUSES) for d in data]
    fig = go.Figure()
    fig.add_bar(
        name="Réponses négatives", x=names, y=negatives, marker_color=RED,
        hovertemplate="%{x}<br>Négatives : %{y:.0f}%<extra></extra>",
    )
    fig.add_bar(
        name="Réponses positives", x=names, y=positives, marker_color=GREEN,
        hovertemplate="%{x}<br>Positives : %{y:.0f}%<extra></extra>",
    )
    fig.update_layout(
        title="Candidatures par CV — taux de réponse (repérer les CV qui engagent)",
        barmode="stack",
        yaxis=dict(title="% des candidatures", ticksuffix="%", range=[0, 100]),
        **PLOTLY_LAYOUT,
    )
    return fig


def figure_last_30_days() -> go.Figure:
    """Répartition par statut des candidatures des 30 derniers jours (barres)."""
    data = stats_last_30_days()
    by_status = data["by_status"]
    if not by_status:
        return _empty_fig("Aucune candidature sur les 30 derniers jours")
    labels = list(by_status.keys())
    values = [by_status[label] for label in labels]
    colors = [status_color(label) for label in labels]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors))
    fig.update_layout(
        title=f"30 derniers jours — {data['total']} candidature(s)",
        **PLOTLY_LAYOUT,
    )
    return fig


def summary_numbers() -> dict:
    """Quelques indicateurs clés pour des tuiles."""
    status_counts = stats_by_current_status()
    last30 = stats_last_30_days()
    total = sum(status_counts.values())
    positives = sum(
        cnt for lbl, cnt in status_counts.items() if lbl in POSITIVE_STATUSES
    )
    return {
        "total": total,
        "refus": status_counts.get("Refus", 0),
        "positives": positives,
        "last_30": last30["total"],
    }
