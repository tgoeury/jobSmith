"""Rapport statistique : figures Plotly (global, par CV, 30 derniers jours)."""
from __future__ import annotations

import plotly.graph_objects as go

from .repository import stats_by_current_status, stats_by_cv, stats_last_30_days
from .ui.theme import (
    ACCENT,
    GREEN,
    PLOTLY_LAYOUT,
    POSITIVE_STATUSES,
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
    """Répartition de toutes les candidatures par statut courant (donut)."""
    counts = stats_by_current_status()
    if not counts:
        return _empty_fig("Aucune candidature")
    labels = list(counts.keys())
    values = [counts[label] for label in labels]
    colors = [status_color(label) for label in labels]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.5,
            marker=dict(colors=colors),
            textinfo="label+value",
        )
    )
    fig.update_layout(title="Statut actuel de toutes les candidatures", **PLOTLY_LAYOUT)
    return fig


def figure_by_cv() -> go.Figure:
    """Par CV : total de candidatures et réponses positives (barres groupées)."""
    data = stats_by_cv()
    if not data:
        return _empty_fig("Aucune candidature")
    data = sorted(data, key=lambda d: d["total"], reverse=True)
    names = [d["cv_name"] for d in data]
    totals = [d["total"] for d in data]
    positives = [
        sum(cnt for lbl, cnt in d["statuses"].items() if lbl in POSITIVE_STATUSES)
        for d in data
    ]
    fig = go.Figure()
    fig.add_bar(name="Candidatures", x=names, y=totals, marker_color=ACCENT)
    fig.add_bar(name="Réponses positives", x=names, y=positives, marker_color=GREEN)
    fig.update_layout(
        title="Candidatures par CV (repérer les meilleures versions)",
        barmode="group",
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
