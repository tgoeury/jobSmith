"""Couche d'accès aux données.

Toutes les fonctions ouvrent leur propre session et renvoient des dictionnaires
(jamais d'objets ORM détachés), ce qui simplifie l'usage côté callbacks Dash.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import SessionLocal
from .models import (
    Application,
    Comment,
    CoverLetter,
    CV,
    StatusEvent,
    StatusType,
)

# ---------------------------------------------------------------------------
# Sérialisation
# ---------------------------------------------------------------------------

def _current_status(app: Application) -> dict | None:
    """Renvoie le dernier événement de statut (le plus récent)."""
    if not app.status_events:
        return None
    latest = max(app.status_events, key=lambda e: (e.changed_at, e.id))
    return {
        "label": latest.status.label,
        "changed_at": latest.changed_at,
        "note": latest.note,
    }


def _application_to_dict(app: Application) -> dict:
    status = _current_status(app)
    return {
        "id": app.id,
        "applied_at": app.applied_at,
        "title": app.title,
        "company": app.company,
        "kind": app.kind or "candidature",
        "contact": app.contact,
        "url": app.url,
        "is_downloadable_url": app.is_downloadable_url,
        "annonce_path": app.annonce_path,
        "annonce_status": app.annonce_status,
        "annonce_note": app.annonce_note,
        "cv_id": app.cv_id,
        "cv_name": app.cv.name if app.cv else None,
        "current_status": status["label"] if status else None,
        "current_status_at": status["changed_at"] if status else None,
        "history": [
            {
                "id": e.id,
                "label": e.status.label,
                "changed_at": e.changed_at,
                "note": e.note,
            }
            for e in sorted(app.status_events, key=lambda x: (x.changed_at, x.id))
        ],
        "comments": [
            {
                "id": c.id,
                "content": c.content,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in sorted(app.comments, key=lambda x: x.created_at)
        ],
    }


def _load_full(session: Session, app_id: int) -> Application | None:
    stmt = (
        select(Application)
        .options(
            selectinload(Application.status_events).selectinload(StatusEvent.status),
            selectinload(Application.comments),
            selectinload(Application.cv),
        )
        .where(Application.id == app_id)
    )
    return session.execute(stmt).scalar_one_or_none()


def _all_full_query():
    return select(Application).options(
        selectinload(Application.status_events).selectinload(StatusEvent.status),
        selectinload(Application.comments),
        selectinload(Application.cv),
    )


# ---------------------------------------------------------------------------
# CV
# ---------------------------------------------------------------------------

def create_cv(name: str, stored_filename: str, original_filename: str,
              uploaded_at: datetime | None = None, make_current: bool = True) -> int:
    with SessionLocal() as session:
        if make_current:
            for cv in session.query(CV).filter(CV.is_current.is_(True)).all():
                cv.is_current = False
        cv = CV(
            name=name,
            stored_filename=stored_filename,
            original_filename=original_filename,
            uploaded_at=uploaded_at or datetime.now(),
            is_current=make_current,
        )
        session.add(cv)
        session.commit()
        return cv.id


def get_current_cv() -> dict | None:
    with SessionLocal() as session:
        cv = session.query(CV).filter(CV.is_current.is_(True)).first()
        return _cv_to_dict(cv) if cv else None


def get_cv(cv_id: int) -> dict | None:
    with SessionLocal() as session:
        cv = session.get(CV, cv_id)
        return _cv_to_dict(cv) if cv else None


def list_cvs() -> list[dict]:
    with SessionLocal() as session:
        cvs = session.query(CV).order_by(CV.uploaded_at.desc()).all()
        return [_cv_to_dict(cv) for cv in cvs]


def _cv_to_dict(cv: CV) -> dict:
    return {
        "id": cv.id,
        "name": cv.name,
        "stored_filename": cv.stored_filename,
        "original_filename": cv.original_filename,
        "uploaded_at": cv.uploaded_at,
        "is_current": cv.is_current,
    }


# ---------------------------------------------------------------------------
# Statuts
# ---------------------------------------------------------------------------

def list_status_types() -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(StatusType)
            .order_by(StatusType.sort_order, StatusType.label)
            .all()
        )
        return [
            {"id": s.id, "label": s.label, "is_system": s.is_system}
            for s in rows
        ]


def get_or_create_status(session: Session, label: str) -> StatusType:
    label = label.strip()
    status = session.query(StatusType).filter(StatusType.label == label).first()
    if status is None:
        status = StatusType(label=label, is_system=False, sort_order=50)
        session.add(status)
        session.flush()
    return status


def add_status_type(label: str) -> dict | None:
    label = (label or "").strip()
    if not label:
        return None
    with SessionLocal() as session:
        status = get_or_create_status(session, label)
        session.commit()
        return {"id": status.id, "label": status.label, "is_system": status.is_system}


# ---------------------------------------------------------------------------
# Candidatures
# ---------------------------------------------------------------------------

def create_application(
    *,
    applied_at: date,
    title: str,
    company: str | None,
    url: str | None,
    cv_id: int | None,
    is_downloadable_url: bool,
    initial_status: str,
    status_at: datetime | None = None,
    kind: str = "candidature",
    contact: str | None = None,
) -> int:
    with SessionLocal() as session:
        app = Application(
            applied_at=applied_at,
            title=title,
            company=company,
            kind=kind,
            contact=contact,
            url=url,
            cv_id=cv_id,
            is_downloadable_url=is_downloadable_url,
            annonce_status="pending" if is_downloadable_url else "na",
        )
        session.add(app)
        session.flush()

        status = get_or_create_status(session, initial_status)
        session.add(
            StatusEvent(
                application_id=app.id,
                status_id=status.id,
                changed_at=status_at or datetime.combine(applied_at, datetime.min.time()),
            )
        )
        session.commit()
        return app.id


def update_application(
    app_id: int,
    *,
    applied_at: date,
    title: str,
    company: str | None,
    url: str | None,
    cv_id: int | None,
    is_downloadable_url: bool,
    kind: str = "candidature",
    contact: str | None = None,
) -> None:
    with SessionLocal() as session:
        app = session.get(Application, app_id)
        if app is None:
            return
        app.applied_at = applied_at
        app.title = title
        app.company = company
        app.kind = kind
        app.contact = contact
        app.url = url
        app.cv_id = cv_id
        app.is_downloadable_url = is_downloadable_url
        if not is_downloadable_url and app.annonce_status != "ok":
            # Une copie saisie manuellement (sans URL) est conservée.
            app.annonce_status = "na"
            app.annonce_path = None
            app.annonce_note = None
        session.commit()


def set_annonce_result(app_id: int, status: str, path: str | None,
                       note: str | None = None) -> None:
    """Enregistre le résultat d'un téléchargement ('ok', 'partial' ou 'failed')."""
    with SessionLocal() as session:
        app = session.get(Application, app_id)
        if app is None:
            return
        app.annonce_status = status
        app.annonce_path = path if status in ("ok", "partial") else None
        app.annonce_note = (note or "")[:300] or None
        session.commit()


def get_application(app_id: int) -> dict | None:
    with SessionLocal() as session:
        app = _load_full(session, app_id)
        return _application_to_dict(app) if app else None


def list_recent_applications(limit: int) -> list[dict]:
    with SessionLocal() as session:
        stmt = (
            _all_full_query()
            .order_by(Application.applied_at.desc(), Application.id.desc())
            .limit(limit)
        )
        apps = session.execute(stmt).scalars().all()
        return [_application_to_dict(a) for a in apps]


def list_all_applications() -> list[dict]:
    with SessionLocal() as session:
        stmt = _all_full_query().order_by(
            Application.applied_at.desc(), Application.id.desc()
        )
        apps = session.execute(stmt).scalars().all()
        return [_application_to_dict(a) for a in apps]


def count_applications() -> int:
    with SessionLocal() as session:
        return session.query(Application).count()


def search_applications(
    *,
    title: str | None = None,
    company: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    """Recherche filtrée. Le filtre `status` porte sur le statut *courant*.

    Les champs texte sont insensibles à la casse (sous-chaîne). Tous les critères
    sont combinés en ET logique ; les critères vides sont ignorés.
    """
    with SessionLocal() as session:
        stmt = _all_full_query()
        if title:
            stmt = stmt.where(Application.title.ilike(f"%{title.strip()}%"))
        if company:
            stmt = stmt.where(Application.company.ilike(f"%{company.strip()}%"))
        if date_from:
            stmt = stmt.where(Application.applied_at >= date_from)
        if date_to:
            stmt = stmt.where(Application.applied_at <= date_to)
        stmt = stmt.order_by(Application.applied_at.desc(), Application.id.desc())
        apps = session.execute(stmt).scalars().all()
        result = [_application_to_dict(a) for a in apps]

    # Le statut courant est calculé après agrégation : filtre en Python.
    if status:
        result = [a for a in result if a["current_status"] == status]
    return result


def list_pending_annonces() -> list[tuple[int, str, str]]:
    """(id, url, intitulé) des candidatures dont la copie locale reste à (re)faire."""
    with SessionLocal() as session:
        rows = (
            session.query(Application.id, Application.url, Application.title)
            .filter(
                Application.is_downloadable_url.is_(True),
                Application.annonce_status.in_(("pending", "failed", "partial")),
            )
            .all()
        )
        return [(r[0], r[1], r[2]) for r in rows]


# ---------------------------------------------------------------------------
# Événements de statut
# ---------------------------------------------------------------------------

def add_status_event(app_id: int, status_label: str, note: str | None = None,
                     changed_at: datetime | None = None) -> None:
    with SessionLocal() as session:
        status = get_or_create_status(session, status_label)
        session.add(
            StatusEvent(
                application_id=app_id,
                status_id=status.id,
                changed_at=changed_at or datetime.now(),
                note=(note or None),
            )
        )
        session.commit()


# ---------------------------------------------------------------------------
# Commentaires
# ---------------------------------------------------------------------------

def add_comment(app_id: int, content: str) -> None:
    content = (content or "").strip()
    if not content:
        return
    with SessionLocal() as session:
        session.add(Comment(application_id=app_id, content=content))
        session.commit()


def update_comment(comment_id: int, content: str) -> None:
    with SessionLocal() as session:
        comment = session.get(Comment, comment_id)
        if comment:
            comment.content = (content or "").strip()
            session.commit()


def delete_comment(comment_id: int) -> None:
    with SessionLocal() as session:
        comment = session.get(Comment, comment_id)
        if comment:
            session.delete(comment)
            session.commit()


# ---------------------------------------------------------------------------
# Lettres de motivation
# ---------------------------------------------------------------------------

def _letter_to_dict(letter: CoverLetter) -> dict:
    return {
        "id": letter.id,
        "name": letter.name,
        "content": letter.content,
        "char_count": letter.char_count,
        "created_at": letter.created_at,
        "updated_at": letter.updated_at,
    }


def list_cover_letters() -> list[dict]:
    with SessionLocal() as session:
        rows = session.query(CoverLetter).order_by(CoverLetter.updated_at.desc()).all()
        return [_letter_to_dict(row) for row in rows]


def get_cover_letter(letter_id: int) -> dict | None:
    with SessionLocal() as session:
        letter = session.get(CoverLetter, letter_id)
        return _letter_to_dict(letter) if letter else None


def create_cover_letter(name: str, content: str = "") -> int:
    with SessionLocal() as session:
        letter = CoverLetter(
            name=name.strip(),
            content=content,
            char_count=len(content or ""),
        )
        session.add(letter)
        session.commit()
        return letter.id


def update_cover_letter(letter_id: int, name: str, content: str) -> None:
    with SessionLocal() as session:
        letter = session.get(CoverLetter, letter_id)
        if letter:
            letter.name = name.strip()
            letter.content = content or ""
            letter.char_count = len(content or "")
            session.commit()


def delete_cover_letter(letter_id: int) -> None:
    with SessionLocal() as session:
        letter = session.get(CoverLetter, letter_id)
        if letter:
            session.delete(letter)
            session.commit()


# ---------------------------------------------------------------------------
# Statistiques (agrégats bruts)
# ---------------------------------------------------------------------------

def stats_by_current_status() -> dict[str, int]:
    counts: dict[str, int] = {}
    for app in list_all_applications():
        label = app["current_status"] or "Inconnu"
        counts[label] = counts.get(label, 0) + 1
    return counts


def stats_by_cv() -> list[dict]:
    """Par CV : nombre de candidatures et de statuts par catégorie."""
    apps = list_all_applications()
    by_cv: dict[str, dict] = {}
    for app in apps:
        cv = app["cv_name"] or "Sans CV"
        entry = by_cv.setdefault(cv, {"cv_name": cv, "total": 0, "statuses": {}})
        entry["total"] += 1
        label = app["current_status"] or "Inconnu"
        entry["statuses"][label] = entry["statuses"].get(label, 0) + 1
    return list(by_cv.values())


def stats_last_30_days() -> dict:
    cutoff = date.today() - timedelta(days=30)
    apps = [a for a in list_all_applications() if a["applied_at"] >= cutoff]
    by_status: dict[str, int] = {}
    for app in apps:
        label = app["current_status"] or "Inconnu"
        by_status[label] = by_status.get(label, 0) + 1
    return {"total": len(apps), "by_status": by_status, "since": cutoff}
