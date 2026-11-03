"""Tests de l'initialisation et de la réinitialisation de la base."""
from __future__ import annotations

from assistant_emploi import repository as repo
from assistant_emploi.database import SYSTEM_STATUSES, create_empty_db, init_db, reset_db


def test_empty_db_has_system_statuses():
    create_empty_db()
    labels = [s["label"] for s in repo.list_status_types()]
    assert "Candidature envoyée" in labels
    assert "Refus" in labels
    assert repo.count_applications() == 0
    assert repo.list_cvs() == []


def test_init_db_is_idempotent():
    init_db()
    init_db()
    # Toujours exactement les deux statuts système, pas de doublon.
    system = [s for s in repo.list_status_types() if s["is_system"]]
    assert len(system) == len(SYSTEM_STATUSES)


def test_reset_db_clears_data():
    from datetime import date

    repo.create_application(
        applied_at=date.today(), title="Poste", company="X", url=None,
        cv_id=None, is_downloadable_url=False, initial_status="Candidature envoyée",
    )
    assert repo.count_applications() == 1
    reset_db()
    assert repo.count_applications() == 0
    # Les statuts système sont recréés après reset.
    assert len(repo.list_status_types()) == len(SYSTEM_STATUSES)


def test_init_db_adds_columns_missing_from_old_schema():
    """Une base créée avant l'ajout de `kind`/`contact` est migrée au démarrage."""
    from sqlalchemy import text

    from assistant_emploi.database import Base, engine

    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        # Schéma minimal de l'ancienne table, sans les colonnes récentes.
        conn.execute(text(
            "CREATE TABLE application (id INTEGER PRIMARY KEY, applied_at DATE, "
            "title VARCHAR(400), company VARCHAR(300), url TEXT, "
            "is_downloadable_url BOOLEAN, annonce_path VARCHAR(300), "
            "annonce_status VARCHAR(20), cv_id INTEGER, created_at DATETIME, "
            "updated_at DATETIME)"
        ))
        conn.execute(text(
            "INSERT INTO application (id, applied_at, title, annonce_status, "
            "is_downloadable_url) VALUES (1, '2026-01-01', 'Ancienne', 'na', 0)"
        ))
    init_db()
    app = repo.get_application(1)
    assert app["kind"] == "candidature"
    assert app["contact"] is None and app["annonce_note"] is None
