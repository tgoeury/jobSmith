"""Test d'import de bout en bout depuis un tableur ODS synthétique."""
from __future__ import annotations

import pandas as pd

from assistant_emploi import repository as repo
from assistant_emploi.ods_import import run_import


def _write_ods(path):
    rows = [
        # num, date, offre, entreprise, url, etat, commentaire
        [1, "2026/01/30", "Data Scientist", "ACME", "Candidatures FT",
         "Candidature envoyé", None],
        [2, "2026/02/06", "ML Engineer", "Neo", "https://example.com/2",
         "Refus", "2026/05/04"],
        [3, "2026/03/01", "AI Engineer", "Zeta", "https://example.com/3",
         "1er entretien", "Bon contact"],
    ]
    df = pd.DataFrame(
        rows,
        columns=["#", "Date", "Offre", "Entreprise", "URL", "État", "Commentaire"],
    )
    df.to_excel(path, engine="odf", index=False)


def test_run_import_creates_applications_and_status_history(tmp_path):
    ods = tmp_path / "candidatures.ods"
    _write_ods(ods)

    rc = run_import(ods_path=ods, download=False)
    assert rc == 0
    assert repo.count_applications() == 3

    apps = {a["title"]: a for a in repo.list_all_applications()}

    # Ligne 1 : « Candidature envoyé » normalisé vers le statut par défaut.
    assert apps["Data Scientist"]["current_status"] == "Candidature envoyée"
    assert len(apps["Data Scientist"]["history"]) == 1

    # Ligne 2 : Refus horodaté à la date du commentaire.
    ml = apps["ML Engineer"]
    assert ml["current_status"] == "Refus"
    refus = [h for h in ml["history"] if h["label"] == "Refus"][0]
    assert refus["changed_at"].date().isoformat() == "2026-05-04"

    # Ligne 3 : statut personnalisé + commentaire texte conservé.
    ai = apps["AI Engineer"]
    assert ai["current_status"] == "1er entretien"
    assert any(c["content"] == "Bon contact" for c in ai["comments"])


def test_run_import_refuses_when_db_not_empty(tmp_path):
    ods = tmp_path / "candidatures.ods"
    _write_ods(ods)
    assert run_import(ods_path=ods, download=False) == 0
    # Deuxième import sans --force -> refusé.
    assert run_import(ods_path=ods, download=False, force=False) == 1
