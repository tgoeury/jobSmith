"""Tests légers des composants liés au CV (marquage « CV inconnu » et alerte)."""
from __future__ import annotations

from assistant_emploi import repository as repo
from assistant_emploi.ui.home import _cv_label, build_cv_section


def _flatten(component, out: list[str]) -> None:
    """Collecte récursivement les identifiants et le texte d'un arbre Dash."""
    cid = getattr(component, "id", None)
    if isinstance(cid, str):
        out.append(cid)
    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            _flatten(child, out)
    elif isinstance(children, str):
        out.append(children)
    elif hasattr(children, "children") or hasattr(children, "to_plotly_json"):
        _flatten(children, out)
    else:
        out.append(str(children))


def _text(component) -> str:
    out: list[str] = []
    _flatten(component, out)
    return " ".join(out)


def test_cv_label_shows_cv_inconnu_when_missing():
    assert "CV inconnu" in _text(_cv_label({"cv_name": None, "kind": "candidature"}))
    with_cv = {"cv_name": "Mon CV", "kind": "candidature"}
    assert "CV inconnu" not in _text(_cv_label(with_cv))
    assert "Mon CV" in _text(_cv_label(with_cv))


def test_cv_label_hidden_for_incoming_contact_without_cv():
    assert _cv_label({"cv_name": None, "kind": "appel"}) is None


def test_cv_section_shows_alert_when_no_cv():
    # Base vide : aucun CV -> l'alerte « no-cv-alert » doit être présente.
    payload = _text(build_cv_section())
    assert "no-cv-alert" in payload
    assert "Aucun CV enregistré" in payload


def test_cv_section_no_alert_when_cv_present():
    repo.create_cv("CV v1", "a.pdf", "CV_v1.pdf", make_current=True)
    payload = _text(build_cv_section())
    assert "no-cv-alert" not in payload
    assert "CV actuel" in payload
