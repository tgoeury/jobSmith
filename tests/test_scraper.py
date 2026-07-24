"""Tests des utilitaires du scraper (sans accès réseau)."""
from __future__ import annotations

import pytest

from assistant_emploi.scraper import _inject_base_tag, is_http_url


@pytest.mark.parametrize(
    "value,expected",
    [
        ("https://www.apec.fr/offre/123", True),
        ("http://example.com", True),
        ("Candidatures FT", False),
        ("", False),
        (None, False),
        ("ftp://example.com/file", False),
        ("   ", False),
    ],
)
def test_is_http_url(value, expected):
    assert is_http_url(value) is expected


def test_inject_base_tag_inside_head():
    html = "<html><head><title>x</title></head><body>hi</body></html>"
    out = _inject_base_tag(html, "https://example.com/page")
    assert '<base href="https://example.com/page">' in out
    # La balise est injectée à l'intérieur du <head>.
    assert out.index("<base") < out.index("</head>")


def test_inject_base_tag_without_head():
    html = "<p>pas de head</p>"
    out = _inject_base_tag(html, "https://example.com")
    assert out.startswith('<base href="https://example.com">')
