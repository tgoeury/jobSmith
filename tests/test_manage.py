"""Tests du CLI de gestion (manage.py)."""
from __future__ import annotations

from datetime import date

from assistant_emploi import repository as repo
from assistant_emploi.database import SYSTEM_STATUSES
from assistant_emploi.manage import main


def test_init_creates_empty_db():
    assert main(["init"]) == 0
    assert repo.count_applications() == 0
    assert len(repo.list_status_types()) == len(SYSTEM_STATUSES)


def test_reset_refuses_without_force_when_data_present():
    repo.create_application(
        applied_at=date.today(), title="X", company=None, url=None,
        cv_id=None, is_downloadable_url=False, initial_status="Candidature envoyée",
    )
    assert main(["reset"]) == 1          # refuse sans --force
    assert repo.count_applications() == 1

    assert main(["reset", "--force"]) == 0
    assert repo.count_applications() == 0
