"""Tests des utilitaires de parsing de la migration ODS."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from assistant_emploi.ods_import import _clean, _parse_date


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026/01/30", date(2026, 1, 30)),
        ("2026-01-30", date(2026, 1, 30)),
        ("30/01/2026", date(2026, 1, 30)),
        ("pas une date", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_parse_date(value, expected):
    assert _parse_date(value) == expected


def test_parse_date_from_timestamp():
    assert _parse_date(pd.Timestamp("2026-03-15")) == date(2026, 3, 15)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("  ACME  ", "ACME"),
        ("", None),
        ("   ", None),
        (None, None),
        (float("nan"), None),
        ("??", "??"),
    ],
)
def test_clean(value, expected):
    assert _clean(value) == expected
