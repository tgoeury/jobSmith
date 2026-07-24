"""Test de l'export ODS."""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from assistant_emploi import repository as repo
from assistant_emploi.exporter import COLUMNS, export_applications_ods


def test_export_produces_valid_ods(tmp_path):
    a1 = repo.create_application(
        applied_at=date(2026, 5, 1), title="Data Scientist", company="ACME",
        url="https://example.com/1", cv_id=None, is_downloadable_url=True,
        initial_status="Candidature envoyée",
    )
    repo.add_status_event(a1, "Refus", changed_at=datetime(2026, 6, 1))
    repo.create_application(
        applied_at=date(2026, 5, 2), title="ML Engineer", company="Neo",
        url="Candidatures FT", cv_id=None, is_downloadable_url=False,
        initial_status="Candidature envoyée",
    )

    out = export_applications_ods(tmp_path / "export.ods")
    assert out.exists()

    df = pd.read_excel(out, engine="odf")
    assert list(df.columns) == COLUMNS
    assert len(df) == 2
    # La ligne dont le dernier statut est « Refus » doit refléter le statut courant.
    refus_row = df[df["Poste"] == "Data Scientist"].iloc[0]
    assert refus_row["Dernier statut"] == "Refus"
    assert refus_row["URL"] == "https://example.com/1"


def test_export_empty_db_has_header_only(tmp_path):
    out = export_applications_ods(tmp_path / "empty.ods")
    df = pd.read_excel(out, engine="odf")
    assert list(df.columns) == COLUMNS
    assert len(df) == 0
