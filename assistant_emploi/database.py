"""Configuration du moteur SQLAlchemy, session et initialisation."""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from .config import DB_PATH
from .models import Base, StatusType

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

# Active l'application des clés étrangères (SQLite les ignore par défaut).
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)

# Statuts livrés par défaut. Le premier est le statut par défaut d'une candidature.
SYSTEM_STATUSES = [
    ("Candidature envoyée", 10),
    ("Contact reçu", 5),  # statut initial d'un contact entrant (RH, chasseur de têtes)
    ("Refus", 90),
]

# Colonnes ajoutées après la création initiale du schéma : `create_all` ne modifie pas
# les tables existantes, on les ajoute donc à la main. (table, colonne, DDL)
_ADDED_COLUMNS = [
    ("application", "kind", "VARCHAR(20) NOT NULL DEFAULT 'candidature'"),
    ("application", "contact", "TEXT"),
    ("application", "annonce_note", "VARCHAR(300)"),
]


def _add_missing_columns() -> None:
    with engine.begin() as conn:
        for table, column, ddl in _ADDED_COLUMNS:
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def init_db() -> None:
    """Crée les tables et insère les statuts système manquants (idempotent)."""
    Base.metadata.create_all(engine)
    _add_missing_columns()
    with SessionLocal() as session:
        existing = {s.label for s in session.query(StatusType).all()}
        for label, order in SYSTEM_STATUSES:
            if label not in existing:
                session.add(
                    StatusType(label=label, is_system=True, sort_order=order)
                )
        session.commit()


def create_empty_db() -> None:
    """Crée une base vide (tables + statuts système), sans aucune donnée.

    Ne touche pas à une base existante ; utiliser `reset_db()` pour repartir de zéro.
    """
    init_db()


def reset_db(drop_files: bool = False) -> None:
    """Vide la base : supprime toutes les tables puis recrée une base vide.

    Si `drop_files` est vrai, supprime aussi le fichier SQLite sur le disque.
    """
    Base.metadata.drop_all(engine)
    if drop_files and DB_PATH.exists():
        engine.dispose()
        DB_PATH.unlink()
    init_db()


@contextmanager
def session_scope():
    """Fournit une session transactionnelle."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
