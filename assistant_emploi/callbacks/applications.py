"""Callbacks des candidatures : rendu, création, édition, statuts, commentaires, export."""
from __future__ import annotations

from datetime import date, datetime

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate

from .. import repository as repo
from ..config import CONFIG
from ..exporter import export_applications_ods
from ..models import APPLICATION_KINDS, DEFAULT_KIND
from ..scraper import download_annonce, is_http_url, save_manual_annonce
from ..ui.home import (
    build_cv_section,
    build_dashboard_body,
    build_stats_section,
    recent_applications,
    render_application_cards,
)

DEFAULT_STATUS = CONFIG.get("default_status", "Candidature envoyée")
# Statut initial d'un contact entrant (appel, mail… d'un RH ou chasseur de têtes).
CONTACT_STATUS = "Contact reçu"


def _clicked() -> bool:
    """True si le callback a été déclenché par un vrai clic (n_clicks non nul)."""
    return bool(ctx.triggered and ctx.triggered[0]["value"])


def _cv_options() -> list[dict]:
    opts = []
    for cv in repo.list_cvs():
        label = cv["name"] + (" (actuel)" if cv["is_current"] else "")
        opts.append({"label": label, "value": str(cv["id"])})
    opts.append({"label": "Aucun CV", "value": ""})
    return opts


def _parse_date_str(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _download_for(app_id: int, url: str | None, title: str | None = None) -> None:
    """Télécharge la copie locale d'une annonce et enregistre le résultat."""
    if is_http_url(url):
        repo.set_annonce_result(app_id, *download_annonce(url, app_id, title))


# ---------------------------------------------------------------------------
# Rendu réactif
# ---------------------------------------------------------------------------

@callback(
    Output("cv-section", "children"),
    Input("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _render_cv(_refresh):
    return build_cv_section()


@callback(
    Output("dashboard-body", "children"),
    Input("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _render_dashboard_body(_refresh):
    return build_dashboard_body()


@callback(
    Output("apps-list", "children"),
    Output("search-summary", "children"),
    Input("active-filters", "data"),
    Input("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _render_apps(filters, _refresh):
    """Rend la liste : résultats filtrés si des filtres sont actifs, sinon les récentes."""
    if filters:
        apps = repo.search_applications(
            title=filters.get("title"),
            company=filters.get("company"),
            status=filters.get("status") or None,
            date_from=_parse_date_str(filters.get("date_from")),
            date_to=_parse_date_str(filters.get("date_to")),
        )
        summary = f"{len(apps)} résultat(s)"
    else:
        apps = recent_applications()
        summary = f"{len(apps)} plus récentes"
    return render_application_cards(apps), summary


@callback(
    Output("active-filters", "data"),
    Input("btn-search", "n_clicks"),
    State("filter-title", "value"),
    State("filter-company", "value"),
    State("filter-status", "value"),
    State("filter-date-from", "value"),
    State("filter-date-to", "value"),
    prevent_initial_call=True,
)
def _apply_filters(_n, title, company, status, date_from, date_to):
    filters: dict = {}
    if (title or "").strip():
        filters["title"] = title.strip()
    if (company or "").strip():
        filters["company"] = company.strip()
    if status:
        filters["status"] = status
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    # Recherche sans critère = affichage des récentes (évite de tout charger).
    return filters or None


@callback(
    Output("active-filters", "data", allow_duplicate=True),
    Output("filter-title", "value"),
    Output("filter-company", "value"),
    Output("filter-status", "value"),
    Output("filter-date-from", "value"),
    Output("filter-date-to", "value"),
    Input("btn-reset-search", "n_clicks"),
    prevent_initial_call=True,
)
def _reset_filters(_n):
    return None, "", "", "", None, None


@callback(
    Output("stats-section", "children"),
    Input("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _render_stats(_refresh):
    return build_stats_section()


# ---------------------------------------------------------------------------
# Modale candidature : ouverture (création + édition)
# ---------------------------------------------------------------------------

@callback(
    Output("app-modal", "is_open"),
    Output("app-modal-title", "children"),
    Output("app-input-date", "value"),
    Output("app-input-title", "value"),
    Output("app-input-company", "value"),
    Output("app-input-kind", "value"),
    Output("app-input-contact", "value"),
    Output("app-input-url", "value"),
    Output("app-input-annonce-text", "value"),
    Output("app-select-cv", "options"),
    Output("app-select-cv", "value"),
    Output("edit-app-id", "data"),
    Output("app-modal-feedback", "children"),
    Input({"type": "btn-new-app", "scope": ALL}, "n_clicks"),
    Input({"type": "edit-app", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def _open_app_modal(_new_clicks, _edit_clicks):
    if not _clicked():
        raise PreventUpdate

    options = _cv_options()
    trigger = ctx.triggered_id

    if isinstance(trigger, dict) and trigger.get("type") == "btn-new-app":
        current = repo.get_current_cv()
        return (
            True,
            "Nouvelle candidature",
            date.today().isoformat(),
            "",
            "",
            DEFAULT_KIND,
            "",
            "",
            "",
            options,
            str(current["id"]) if current else "",
            None,
            "",
        )

    # Édition
    app_id = trigger["index"]
    app = repo.get_application(app_id)
    if not app:
        raise PreventUpdate
    return (
        True,
        f"Éditer la candidature #{app_id}",
        app["applied_at"].isoformat() if app["applied_at"] else "",
        app["title"] or "",
        app["company"] or "",
        app["kind"],
        app["contact"] or "",
        app["url"] or "",
        "",
        options,
        str(app["cv_id"]) if app["cv_id"] else "",
        app_id,
        "",
    )


@callback(
    Output("app-label-date", "children"),
    Output("app-label-title", "children"),
    Output("app-select-cv", "value", allow_duplicate=True),
    Input("app-input-kind", "value"),
    State("edit-app-id", "data"),
    prevent_initial_call=True,
)
def _on_kind_change(kind, edit_id):
    """Adapte les libellés au type d'entrée ; en création, propose le CV adapté."""
    is_application = (kind or DEFAULT_KIND) == DEFAULT_KIND
    date_label = "Date de candidature" if is_application else "Date du contact"
    title_label = "Intitulé du poste *" if is_application else "Intitulé du poste"
    if edit_id:
        cv_value = no_update  # ne jamais écraser le CV d'une entrée existante
    elif is_application:
        current = repo.get_current_cv()
        cv_value = str(current["id"]) if current else ""
    else:
        cv_value = ""  # un contact entrant n'est pas lié à un CV envoyé
    return date_label, title_label, cv_value


@callback(
    Output("app-modal", "is_open", allow_duplicate=True),
    Input("app-modal-cancel", "n_clicks"),
    prevent_initial_call=True,
)
def _cancel_app_modal(_n):
    return False


@callback(
    Output("app-modal", "is_open", allow_duplicate=True),
    Output("refresh-apps", "data", allow_duplicate=True),
    Output("app-modal-feedback", "children", allow_duplicate=True),
    Output("action-feedback", "children", allow_duplicate=True),
    Input("app-modal-save", "n_clicks"),
    State("app-input-date", "value"),
    State("app-input-title", "value"),
    State("app-input-company", "value"),
    State("app-input-kind", "value"),
    State("app-input-contact", "value"),
    State("app-input-url", "value"),
    State("app-input-annonce-text", "value"),
    State("app-select-cv", "value"),
    State("edit-app-id", "data"),
    State("refresh-apps", "data"),
    prevent_initial_call=True,
    # Le téléchargement de l'annonce peut prendre plusieurs secondes.
    running=[
        (Output("app-modal-save", "disabled"), True, False),
        (Output("app-modal-save", "children"), "Enregistrement…", "Enregistrer"),
    ],
)
def _save_app(_n, date_str, title, company, kind, contact, url, annonce_text,
              cv_value, edit_id, refresh):
    kind = kind if kind in APPLICATION_KINDS else DEFAULT_KIND
    title = (title or "").strip()
    if not title:
        if kind == DEFAULT_KIND:
            return no_update, no_update, dbc.Alert(
                "L'intitulé du poste est obligatoire.", color="danger",
                class_name="py-2 mb-0",
            ), no_update
        title = "Poste non précisé"

    applied = _parse_date_str(date_str) or date.today()
    url = (url or "").strip() or None
    company = (company or "").strip() or None
    contact = (contact or "").strip() or None
    annonce_text = (annonce_text or "").strip()
    cv_id = int(cv_value) if cv_value else None
    downloadable = is_http_url(url)

    if edit_id:
        old = repo.get_application(edit_id)
        repo.update_application(
            edit_id,
            applied_at=applied,
            title=title,
            company=company,
            kind=kind,
            contact=contact,
            url=url,
            cv_id=cv_id,
            is_downloadable_url=downloadable,
        )
        if annonce_text:
            repo.set_annonce_result(edit_id, *save_manual_annonce(edit_id, annonce_text, url))
        # (Re)télécharge si l'URL a changé ou si la copie n'est pas encore OK.
        elif downloadable and (
            not old or old["url"] != url or old["annonce_status"] != "ok"
        ):
            _download_for(edit_id, url, title)
        msg = "Entrée mise à jour."
    else:
        new_id = repo.create_application(
            applied_at=applied,
            title=title,
            company=company,
            kind=kind,
            contact=contact,
            url=url,
            cv_id=cv_id,
            is_downloadable_url=downloadable,
            initial_status=DEFAULT_STATUS if kind == DEFAULT_KIND else CONTACT_STATUS,
        )
        # Téléchargement APRÈS enregistrement en base.
        if annonce_text:
            repo.set_annonce_result(new_id, *save_manual_annonce(new_id, annonce_text, url))
        else:
            _download_for(new_id, url, title)
        msg = "Candidature enregistrée." if kind == DEFAULT_KIND else "Contact enregistré."

    feedback = dbc.Alert(msg, color="success", class_name="py-2 mb-0", duration=3000)
    return False, (refresh or 0) + 1, "", feedback


# ---------------------------------------------------------------------------
# Modale statut
# ---------------------------------------------------------------------------

_DELETE_HIDDEN = {"display": "none"}
_DELETE_SHOWN = {"color": "var(--red)"}


@callback(
    Output("status-modal", "is_open"),
    Output("status-modal-title", "children"),
    Output("status-select-label", "children"),
    Output("status-modal-app-label", "children"),
    Output("status-select", "options"),
    Output("status-select", "value"),
    Output("status-date", "value"),
    Output("status-note", "value"),
    Output("status-app-id", "data"),
    Output("status-event-id", "data"),
    Output("status-modal-delete", "style"),
    Output("status-modal-feedback", "children"),
    Input({"type": "status-app", "index": ALL}, "n_clicks"),
    Input({"type": "edit-status-event", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def _open_status_modal(_new_clicks, _edit_clicks):
    """Ouvre la modale statut : nouvelle étape, ou édition d'une étape existante."""
    if not _clicked():
        raise PreventUpdate
    trigger = ctx.triggered_id
    event = None
    if trigger["type"] == "edit-status-event":
        event = repo.get_status_event(trigger["index"])
        if not event:
            raise PreventUpdate
        app_id = event["application_id"]
    else:
        app_id = trigger["index"]
    app = repo.get_application(app_id)
    if not app:
        raise PreventUpdate
    options = [{"label": s["label"], "value": s["label"]} for s in repo.list_status_types()]
    label = f"{app['title']} — {app['company'] or ''}"
    if event:
        return (
            True,
            "Modifier l'étape",
            "Statut",
            label,
            options,
            event["label"],
            event["changed_at"].date().isoformat(),
            event["note"] or "",
            app_id,
            event["id"],
            _DELETE_SHOWN,
            "",
        )
    return (
        True,
        "Changer le statut",
        "Nouveau statut",
        label,
        options,
        app["current_status"],
        date.today().isoformat(),
        "",
        app_id,
        None,
        _DELETE_HIDDEN,
        "",
    )


@callback(
    Output("status-select", "options", allow_duplicate=True),
    Output("status-select", "value", allow_duplicate=True),
    Output("new-status-input", "value"),
    Output("status-modal-feedback", "children", allow_duplicate=True),
    Input("add-status-btn", "n_clicks"),
    State("new-status-input", "value"),
    prevent_initial_call=True,
)
def _add_status_type(_n, new_label):
    new_label = (new_label or "").strip()
    if not new_label:
        raise PreventUpdate
    repo.add_status_type(new_label)
    options = [{"label": s["label"], "value": s["label"]} for s in repo.list_status_types()]
    feedback = dbc.Alert(
        f"Statut « {new_label} » ajouté.", color="success", class_name="py-1 mb-0",
        duration=2500,
    )
    return options, new_label, "", feedback


@callback(
    Output("status-modal", "is_open", allow_duplicate=True),
    Input("status-modal-cancel", "n_clicks"),
    prevent_initial_call=True,
)
def _cancel_status_modal(_n):
    return False


@callback(
    Output("status-modal", "is_open", allow_duplicate=True),
    Output("refresh-apps", "data", allow_duplicate=True),
    Input("status-modal-save", "n_clicks"),
    State("status-select", "value"),
    State("status-note", "value"),
    State("status-date", "value"),
    State("status-app-id", "data"),
    State("status-event-id", "data"),
    State("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _save_status(_n, status_label, note, date_str, app_id, event_id, refresh):
    if not app_id or not status_label:
        raise PreventUpdate
    note = (note or "").strip() or None
    changed_on = _parse_date_str(date_str)
    if event_id:
        event = repo.get_status_event(event_id)
        if not event:
            raise PreventUpdate
        # On garde l'heure d'origine : elle départage les étapes d'un même jour.
        old = event["changed_at"]
        changed_at = datetime.combine(changed_on, old.time()) if changed_on else old
        repo.update_status_event(event_id, status_label, changed_at, note=note)
    else:
        changed_at = (
            datetime.combine(changed_on, datetime.now().time())
            if changed_on
            else datetime.now()
        )
        repo.add_status_event(app_id, status_label, note=note, changed_at=changed_at)
    return False, (refresh or 0) + 1


@callback(
    Output("status-modal", "is_open", allow_duplicate=True),
    Output("refresh-apps", "data", allow_duplicate=True),
    Output("status-modal-feedback", "children", allow_duplicate=True),
    Input("status-modal-delete", "n_clicks"),
    State("status-event-id", "data"),
    State("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _delete_status_event(_n, event_id, refresh):
    if not event_id:
        raise PreventUpdate
    if not repo.delete_status_event(event_id):
        return no_update, no_update, dbc.Alert(
            "Impossible de supprimer la seule étape de la candidature : "
            "modifiez-la plutôt.",
            color="warning", class_name="py-2 mb-0",
        )
    return False, (refresh or 0) + 1, ""


# ---------------------------------------------------------------------------
# Commentaires
# ---------------------------------------------------------------------------

@callback(
    Output("refresh-apps", "data", allow_duplicate=True),
    Input({"type": "new-comment-btn", "index": ALL}, "n_clicks"),
    State({"type": "new-comment-input", "index": ALL}, "value"),
    State("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _add_comment(_clicks, _values, refresh):
    if not _clicked():
        raise PreventUpdate
    app_id = ctx.triggered_id["index"]
    mapping = {s["id"]["index"]: s.get("value") for s in ctx.states_list[0]}
    content = (mapping.get(app_id) or "").strip()
    if not content:
        raise PreventUpdate
    repo.add_comment(app_id, content)
    return (refresh or 0) + 1


@callback(
    Output("comment-modal", "is_open"),
    Output("comment-modal-textarea", "value"),
    Output("comment-edit-id", "data"),
    Input({"type": "edit-comment", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def _open_comment_modal(_clicks):
    if not _clicked():
        raise PreventUpdate
    comment_id = ctx.triggered_id["index"]
    # Recherche du contenu du commentaire.
    content = ""
    for app in repo.list_all_applications():
        for comment in app["comments"]:
            if comment["id"] == comment_id:
                content = comment["content"]
                break
    return True, content, comment_id


@callback(
    Output("comment-modal", "is_open", allow_duplicate=True),
    Input("comment-modal-cancel", "n_clicks"),
    prevent_initial_call=True,
)
def _cancel_comment_modal(_n):
    return False


@callback(
    Output("comment-modal", "is_open", allow_duplicate=True),
    Output("refresh-apps", "data", allow_duplicate=True),
    Input("comment-modal-save", "n_clicks"),
    State("comment-modal-textarea", "value"),
    State("comment-edit-id", "data"),
    State("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _save_comment(_n, content, comment_id, refresh):
    if not comment_id:
        raise PreventUpdate
    repo.update_comment(comment_id, content or "")
    return False, (refresh or 0) + 1


@callback(
    Output("comment-modal", "is_open", allow_duplicate=True),
    Output("refresh-apps", "data", allow_duplicate=True),
    Input("comment-modal-delete", "n_clicks"),
    State("comment-edit-id", "data"),
    State("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _delete_comment(_n, comment_id, refresh):
    if not comment_id:
        raise PreventUpdate
    repo.delete_comment(comment_id)
    return False, (refresh or 0) + 1


# ---------------------------------------------------------------------------
# Export ODS & re-téléchargement des copies manquantes
# ---------------------------------------------------------------------------

@callback(
    Output("download-ods", "data"),
    Input("btn-export-ods", "n_clicks"),
    prevent_initial_call=True,
)
def _export_ods(_n):
    # Le bouton apparaît (n_clicks=0) à chaque ouverture de la page : pas un clic.
    if not _clicked():
        raise PreventUpdate
    path = export_applications_ods()
    return dcc.send_file(str(path))


@callback(
    Output("refresh-apps", "data", allow_duplicate=True),
    Output("action-feedback", "children", allow_duplicate=True),
    Input("btn-retry-annonces", "n_clicks"),
    State("refresh-apps", "data"),
    prevent_initial_call=True,
)
def _retry_annonces(_n, refresh):
    if not _clicked():
        raise PreventUpdate
    targets = repo.list_pending_annonces()
    ok = 0
    for app_id, url, title in targets:
        prev = repo.get_application(app_id)
        _download_for(app_id, url, title)
        after = repo.get_application(app_id)
        if after and after["annonce_status"] == "ok" and (
            not prev or prev["annonce_status"] != "ok"
        ):
            ok += 1
    feedback = dbc.Alert(
        f"{ok} nouvelle(s) copie(s) récupérée(s) sur {len(targets)} tentative(s).",
        color="info", class_name="py-2 mb-0", duration=4000,
    )
    return (refresh or 0) + 1, feedback
