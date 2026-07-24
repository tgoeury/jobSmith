"""Tests de la recherche filtrée des candidatures."""
from __future__ import annotations

from datetime import date, datetime

from assistant_emploi import repository as repo


def _seed():
    a1 = repo.create_application(
        applied_at=date(2026, 1, 10), title="Data Scientist", company="ACME Corp",
        url=None, cv_id=None, is_downloadable_url=False,
        initial_status="Candidature envoyée",
    )
    a2 = repo.create_application(
        applied_at=date(2026, 3, 15), title="ML Engineer", company="Neo Labs",
        url=None, cv_id=None, is_downloadable_url=False,
        initial_status="Candidature envoyée",
    )
    a3 = repo.create_application(
        applied_at=date(2026, 6, 20), title="Senior Data Scientist", company="ACME Corp",
        url=None, cv_id=None, is_downloadable_url=False,
        initial_status="Candidature envoyée",
    )
    repo.add_status_event(a3, "Refus", changed_at=datetime(2026, 7, 1))
    return a1, a2, a3


def test_search_by_title_is_case_insensitive_substring():
    _seed()
    res = repo.search_applications(title="data scientist")
    titles = sorted(a["title"] for a in res)
    assert titles == ["Data Scientist", "Senior Data Scientist"]


def test_search_by_company():
    _seed()
    res = repo.search_applications(company="acme")
    assert len(res) == 2
    assert all(a["company"] == "ACME Corp" for a in res)


def test_search_by_current_status():
    _seed()
    res = repo.search_applications(status="Refus")
    assert len(res) == 1
    assert res[0]["title"] == "Senior Data Scientist"

    res_sent = repo.search_applications(status="Candidature envoyée")
    assert len(res_sent) == 2  # a3 est passé en Refus


def test_search_by_date_range():
    _seed()
    res = repo.search_applications(
        date_from=date(2026, 3, 1), date_to=date(2026, 6, 30)
    )
    titles = sorted(a["title"] for a in res)
    assert titles == ["ML Engineer", "Senior Data Scientist"]


def test_search_combined_filters():
    _seed()
    res = repo.search_applications(company="acme", status="Candidature envoyée")
    assert len(res) == 1
    assert res[0]["title"] == "Data Scientist"


def test_search_no_criteria_returns_all():
    _seed()
    assert len(repo.search_applications()) == 3


def test_search_results_ordered_by_date_desc():
    _seed()
    res = repo.search_applications(company="acme")
    assert res[0]["applied_at"] >= res[-1]["applied_at"]
