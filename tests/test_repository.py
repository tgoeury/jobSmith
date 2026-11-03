"""Tests de la couche d'accès aux données (repository)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from assistant_emploi import repository as repo


# ---------------------------------------------------------------------------
# Candidatures & statuts
# ---------------------------------------------------------------------------

def _make_app(title="Data Scientist", status="Candidature envoyée",
              url=None, downloadable=False, applied=None, cv_id=None):
    return repo.create_application(
        applied_at=applied or date.today(),
        title=title,
        company="ACME",
        url=url,
        cv_id=cv_id,
        is_downloadable_url=downloadable,
        initial_status=status,
    )


def test_create_application_sets_initial_status_and_na_annonce():
    app_id = _make_app(url="Candidatures FT", downloadable=False)
    app = repo.get_application(app_id)
    assert app["current_status"] == "Candidature envoyée"
    assert app["annonce_status"] == "na"
    assert len(app["history"]) == 1


def test_downloadable_url_starts_pending():
    app_id = _make_app(url="https://example.com/offre", downloadable=True)
    app = repo.get_application(app_id)
    assert app["annonce_status"] == "pending"
    assert (app_id, "https://example.com/offre", "Data Scientist") in repo.list_pending_annonces()


def test_current_status_is_latest_by_changed_at():
    app_id = _make_app(applied=date.today() - timedelta(days=10))
    # Refus plus récent -> devient le statut courant.
    repo.add_status_event(app_id, "Refus", changed_at=datetime.now())
    app = repo.get_application(app_id)
    assert app["current_status"] == "Refus"
    assert len(app["history"]) == 2

    # Un événement plus ANCIEN ne doit pas redevenir le statut courant.
    repo.add_status_event(
        app_id, "1er entretien", changed_at=datetime.now() - timedelta(days=30)
    )
    app = repo.get_application(app_id)
    assert app["current_status"] == "Refus"


def test_update_application_changes_fields():
    app_id = _make_app(title="Ancien titre")
    repo.update_application(
        app_id, applied_at=date(2026, 1, 1), title="Nouveau titre",
        company="Neo", url=None, cv_id=None, is_downloadable_url=False,
    )
    app = repo.get_application(app_id)
    assert app["title"] == "Nouveau titre"
    assert app["company"] == "Neo"
    assert app["applied_at"] == date(2026, 1, 1)


def test_list_recent_respects_limit_and_order():
    older = _make_app(title="Vieux", applied=date(2026, 1, 1))
    newer = _make_app(title="Recent", applied=date(2026, 6, 1))
    recent = repo.list_recent_applications(1)
    assert len(recent) == 1
    assert recent[0]["id"] == newer
    assert older != newer


# ---------------------------------------------------------------------------
# Types de statut
# ---------------------------------------------------------------------------

def test_add_status_type_is_idempotent():
    repo.add_status_type("1er entretien")
    repo.add_status_type("1er entretien")
    labels = [s["label"] for s in repo.list_status_types()]
    assert labels.count("1er entretien") == 1


def test_add_status_event_creates_unknown_status():
    app_id = _make_app()
    repo.add_status_event(app_id, "Statut inédit")
    labels = [s["label"] for s in repo.list_status_types()]
    assert "Statut inédit" in labels


# ---------------------------------------------------------------------------
# Commentaires
# ---------------------------------------------------------------------------

def test_comment_add_update_delete():
    app_id = _make_app()
    repo.add_comment(app_id, "  Premier commentaire  ")
    app = repo.get_application(app_id)
    assert len(app["comments"]) == 1
    assert app["comments"][0]["content"] == "Premier commentaire"  # trim

    comment_id = app["comments"][0]["id"]
    repo.update_comment(comment_id, "Modifié")
    app = repo.get_application(app_id)
    assert app["comments"][0]["content"] == "Modifié"

    repo.delete_comment(comment_id)
    app = repo.get_application(app_id)
    assert app["comments"] == []


def test_empty_comment_is_ignored():
    app_id = _make_app()
    repo.add_comment(app_id, "   ")
    app = repo.get_application(app_id)
    assert app["comments"] == []


# ---------------------------------------------------------------------------
# CV
# ---------------------------------------------------------------------------

def test_create_cv_sets_current_and_unsets_previous():
    cv1 = repo.create_cv("CV v1", "a.pdf", "CV_v1.pdf", make_current=True)
    cv2 = repo.create_cv("CV v2", "b.pdf", "CV_v2.pdf", make_current=True)
    current = repo.get_current_cv()
    assert current["id"] == cv2
    assert repo.get_cv(cv1)["is_current"] is False
    assert len(repo.list_cvs()) == 2


# ---------------------------------------------------------------------------
# Lettres de motivation
# ---------------------------------------------------------------------------

def test_cover_letter_crud_and_char_count():
    letter_id = repo.create_cover_letter("Type A", "abcde")
    letter = repo.get_cover_letter(letter_id)
    assert letter["char_count"] == 5

    repo.update_cover_letter(letter_id, "Type A", "abcdefghij")
    letter = repo.get_cover_letter(letter_id)
    assert letter["char_count"] == 10
    assert letter["name"] == "Type A"

    repo.delete_cover_letter(letter_id)
    assert repo.get_cover_letter(letter_id) is None


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------

def test_stats_by_current_status():
    _make_app()
    refused = _make_app()
    repo.add_status_event(refused, "Refus", changed_at=datetime.now())
    counts = repo.stats_by_current_status()
    assert counts.get("Candidature envoyée") == 1
    assert counts.get("Refus") == 1


def test_stats_last_30_days_excludes_old():
    _make_app(applied=date.today())
    _make_app(applied=date.today() - timedelta(days=60))
    data = repo.stats_last_30_days()
    assert data["total"] == 1


def test_stats_by_cv_groups_and_counts():
    cv_id = repo.create_cv("CV v1", "a.pdf", "CV_v1.pdf")
    _make_app(cv_id=cv_id)
    _make_app(cv_id=cv_id)
    _make_app(cv_id=None)
    stats = {row["cv_name"]: row["total"] for row in repo.stats_by_cv()}
    assert stats.get("CV v1") == 2
    assert stats.get("Sans CV") == 1


# ---------------------------------------------------------------------------
# Contacts entrants & résultat des copies d'annonces
# ---------------------------------------------------------------------------

def test_incoming_contact_kind_and_contact_are_stored():
    app_id = repo.create_application(
        applied_at=date.today(), title="Lead Data", company="Cabinet X",
        url=None, cv_id=None, is_downloadable_url=False,
        initial_status="Contact reçu", kind="appel", contact="Jeanne, 06 00 00 00 00",
    )
    app = repo.get_application(app_id)
    assert app["kind"] == "appel"
    assert app["contact"] == "Jeanne, 06 00 00 00 00"
    assert app["current_status"] == "Contact reçu"


def test_default_kind_is_candidature():
    app = repo.get_application(_make_app())
    assert app["kind"] == "candidature"
    assert app["contact"] is None


def test_partial_annonce_keeps_path_and_is_retried():
    app_id = _make_app(url="https://example.com/offre", downloadable=True)
    repo.set_annonce_result(app_id, "partial", "1.html", "copie douteuse")
    app = repo.get_application(app_id)
    assert (app["annonce_status"], app["annonce_path"]) == ("partial", "1.html")
    assert app["annonce_note"] == "copie douteuse"
    assert app_id in [t[0] for t in repo.list_pending_annonces()]


def test_failed_annonce_drops_path():
    app_id = _make_app(url="https://example.com/offre", downloadable=True)
    repo.set_annonce_result(app_id, "failed", "1.html", "HTTP 403")
    app = repo.get_application(app_id)
    assert app["annonce_path"] is None
    assert app["annonce_note"] == "HTTP 403"


def test_manual_copy_without_url_survives_edit():
    app_id = _make_app()
    repo.set_annonce_result(app_id, "ok", "1.html", "copie saisie manuellement")
    repo.update_application(
        app_id, applied_at=date.today(), title="Data Scientist", company="ACME",
        url=None, cv_id=None, is_downloadable_url=False,
    )
    assert repo.get_application(app_id)["annonce_status"] == "ok"
