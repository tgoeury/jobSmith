"""Modèles SQLAlchemy pour l'assistant de recherche d'emploi."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Nature d'une entrée du suivi : candidature envoyée ou contact entrant (RH, chasseur
# de têtes…). Clé stockée en base -> libellé affiché.
APPLICATION_KINDS = {
    "candidature": "Candidature",
    "appel": "Appel reçu",
    "mail": "Mail reçu",
    "message": "Message reçu (LinkedIn…)",
}
DEFAULT_KIND = "candidature"


class CV(Base):
    __tablename__ = "cv"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    applications: Mapped[list["Application"]] = relationship(back_populates="cv")


class StatusType(Base):
    __tablename__ = "status_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(120), unique=True)
    # Statut « système » : livré par défaut, non supprimable.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)

    events: Mapped[list["StatusEvent"]] = relationship(back_populates="status")


class Application(Base):
    __tablename__ = "application"

    id: Mapped[int] = mapped_column(primary_key=True)
    applied_at: Mapped[date] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(400))
    company: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Clé de APPLICATION_KINDS.
    kind: Mapped[str] = mapped_column(
        String(20), default=DEFAULT_KIND, server_default=DEFAULT_KIND
    )
    # Interlocuteur (nom, cabinet, téléphone, e-mail…), texte libre.
    contact: Mapped[str | None] = mapped_column(Text, nullable=True)
    # URL de l'annonce OU moyen de candidater (ex. « Candidatures FT »).
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # True si `url` est une vraie URL http(s) téléchargeable.
    is_downloadable_url: Mapped[bool] = mapped_column(Boolean, default=False)
    # Chemin relatif de la copie locale de l'annonce (dans data/annonces/).
    annonce_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # 'na' (pas d'URL), 'pending', 'ok', 'partial' (copie douteuse), 'failed'.
    annonce_status: Mapped[str] = mapped_column(String(20), default="na")
    # Explication du dernier téléchargement (raison de l'échec, méthode utilisée…).
    annonce_note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    cv_id: Mapped[int | None] = mapped_column(ForeignKey("cv.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    cv: Mapped["CV | None"] = relationship(back_populates="applications")
    status_events: Mapped[list["StatusEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="StatusEvent.changed_at",
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
    )


class StatusEvent(Base):
    __tablename__ = "status_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("application.id", ondelete="CASCADE")
    )
    status_id: Mapped[int] = mapped_column(ForeignKey("status_type.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    application: Mapped["Application"] = relationship(back_populates="status_events")
    status: Mapped["StatusType"] = relationship(back_populates="events")


class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("application.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    application: Mapped["Application"] = relationship(back_populates="comments")


class CoverLetter(Base):
    __tablename__ = "cover_letter"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, default="")
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (UniqueConstraint("name", name="uq_cover_letter_name"),)
