"""Fixtures de test : base SQLite isolée dans un dossier temporaire.

La variable d'environnement doit être posée AVANT tout import du paquet, car
`assistant_emploi.config` lit le dossier de données à l'import et
`assistant_emploi.database` crée le moteur à partir de ce chemin.
"""
from __future__ import annotations

import os
import shutil
import tempfile

# Dossier de données temporaire, valable pour toute la session de test.
_TMP_DATA_DIR = tempfile.mkdtemp(prefix="assistant_emploi_test_")
os.environ["ASSISTANT_EMPLOI_DATA_DIR"] = _TMP_DATA_DIR

import pytest  # noqa: E402

from assistant_emploi.database import Base, engine, init_db  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    """Repart d'une base vide avant chaque test."""
    Base.metadata.drop_all(engine)
    init_db()
    yield
    Base.metadata.drop_all(engine)


def pytest_sessionfinish(session, exitstatus):  # noqa: ANN001
    """Nettoie le dossier temporaire à la fin de la session."""
    engine.dispose()
    shutil.rmtree(_TMP_DATA_DIR, ignore_errors=True)
