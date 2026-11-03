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


# ---------------------------------------------------------------------------
# download_annonce : évaluation du contenu et repli navigateur (sans réseau)
# ---------------------------------------------------------------------------

import json  # noqa: E402

from assistant_emploi import scraper  # noqa: E402
from assistant_emploi.config import ANNONCES_DIR  # noqa: E402

URL = "https://jobs.example.com/offre/42"
FILLER = "Missions, profil recherché, avantages et processus de recrutement. " * 40


def _page(body: str, status: int = 200, via: str = "http", head: str = "") -> scraper._Page:
    html = f"<html><head><title>t</title>{head}</head><body>{body}</body></html>"
    return scraper._Page(html, URL, status, via)


def _ld(job: dict) -> str:
    # Comme sur les vrais sites, « </ » est échappé pour ne pas clore la balise.
    payload = json.dumps(job).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


@pytest.fixture
def fetchers(monkeypatch):
    """Remplace les deux méthodes de récupération ; enregistre les appels."""
    calls = {"http": 0, "browser": 0}
    pages = {"http": (None, "échec"), "browser": (None, "indisponible")}

    def fake_http(_url):
        calls["http"] += 1
        return pages["http"]

    def fake_browser(_url):
        calls["browser"] += 1
        return pages["browser"]

    monkeypatch.setattr(scraper, "_fetch_http", fake_http)
    monkeypatch.setattr(scraper, "_fetch_browser", fake_browser)
    return pages, calls


def test_good_static_page_skips_browser(fetchers):
    pages, calls = fetchers
    pages["http"] = (_page(f"<h1>Data Scientist H/F</h1><p>{FILLER}</p>"), "")
    result = scraper.download_annonce(URL, 1, "Data Scientist")
    assert result.status == "ok"
    assert calls["browser"] == 0
    assert (ANNONCES_DIR / result.path).exists()


def test_js_shell_falls_back_to_browser(fetchers):
    pages, calls = fetchers
    pages["http"] = (_page("<div id='app'>Loading...</div><script>boot()</script>"), "")
    pages["browser"] = (
        _page(f"<h1>Data Scientist</h1><p>{FILLER}</p>", via="navigateur"), ""
    )
    result = scraper.download_annonce(URL, 2, "Data Scientist")
    assert calls["browser"] == 1
    assert result.status == "ok"
    assert "navigateur" in result.note


def test_blocked_static_page_falls_back_to_browser(fetchers):
    pages, calls = fetchers
    pages["http"] = (_page("Just a moment...", status=403), "")
    pages["browser"] = (_page(f"<h1>ML Engineer</h1>{FILLER}", via="navigateur"), "")
    assert scraper.download_annonce(URL, 3, "ML Engineer").status == "ok"
    assert calls["browser"] == 1


def test_everything_empty_is_reported_as_failure(fetchers):
    pages, _calls = fetchers
    pages["http"] = (_page("Please enable JavaScript to continue."), "")
    result = scraper.download_annonce(URL, 4, "Data Scientist")
    assert result.status == "failed"
    assert result.path is None
    assert "JavaScript" in result.note


def test_expired_ad_does_not_try_browser(fetchers):
    pages, calls = fetchers
    pages["http"] = (_page("Offre introuvable", status=404), "")
    result = scraper.download_annonce(URL, 5, "Data Scientist")
    assert result.status == "failed" and "404" in result.note
    assert calls["browser"] == 0


def test_page_without_the_title_is_partial(fetchers):
    pages, _calls = fetchers
    pages["http"] = (_page(f"<h1>Toutes nos offres</h1><p>{FILLER}</p>"), "")
    result = scraper.download_annonce(URL, 6, "Data Scientist")
    assert result.status == "partial"
    assert result.path is not None


def test_job_posting_json_ld_rebuilds_empty_page(fetchers):
    pages, _calls = fetchers
    job = {
        "@context": "https://schema.org",
        "@graph": [{
            "@type": "JobPosting",
            "title": "Data Scientist",
            "description": "<p>Analyser des données</p><script>alert(1)</script>",
            "hiringOrganization": {"@type": "Organization", "name": "ACME"},
            "jobLocation": {"address": {"addressLocality": "Toulouse"}},
        }],
    }
    pages["http"] = (_page("<div id='root'></div>", head=_ld(job)), "")
    result = scraper.download_annonce(URL, 7, "Autre intitulé")
    assert result.status == "ok"
    saved = (ANNONCES_DIR / result.path).read_text(encoding="utf-8")
    assert "Analyser des données" in saved
    assert "ACME" in saved and "Toulouse" in saved
    assert "<script" not in saved


def test_saved_copy_has_no_executable_scripts(fetchers):
    pages, _calls = fetchers
    body = f"<h1>Data Scientist</h1><p>{FILLER}</p><script src='cmp.js'></script>"
    head = _ld({"@type": "Organization"}) + (
        '<link rel="stylesheet" href="https://cdn.example.com/a.css" crossorigin="" '
        'integrity="sha384-x">'
    )
    pages["http"] = (_page(body, head=head), "")
    result = scraper.download_annonce(URL, 8, "Data Scientist")
    saved = (ANNONCES_DIR / result.path).read_text(encoding="utf-8")
    assert "cmp.js" not in saved
    assert "application/ld+json" in saved
    assert f'<base href="{URL}">' in saved
    assert '<link rel="stylesheet" href="https://cdn.example.com/a.css">' in saved


def test_manual_copy_is_escaped():
    result = scraper.save_manual_annonce(9, "Poste <b>IA</b>\n- Python", URL)
    assert result.status == "ok"
    saved = (ANNONCES_DIR / result.path).read_text(encoding="utf-8")
    assert "&lt;b&gt;IA&lt;/b&gt;" in saved
    assert "- Python" in saved
