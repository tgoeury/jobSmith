"""Import de candidatures depuis un tableur OpenDocument (.ods).

Le fichier doit comporter une ligne d'en-tête et des colonnes dans cet ordre :

    numéro (ignoré) | date | intitulé du poste | entreprise | URL ou moyen | état | commentaire

- La date accepte les formats `AAAA/MM/JJ`, `AAAA-MM-JJ` ou `JJ/MM/AAAA`.
- La colonne « état » alimente le statut ; toute valeur différente du statut par
  défaut crée un événement de statut supplémentaire.
- Pour une ligne dont l'état n'est pas le statut par défaut, si la colonne
  « commentaire » contient une date, elle horodate le changement de statut ;
  sinon le texte devient un commentaire.
- Si l'URL est http(s), une copie locale de l'annonce est téléchargée (best-effort).

Usage :
    python -m assistant_emploi.ods_import --file candidatures.ods [--cv CV.pdf]
                                          [--no-download] [--force]
    python -m assistant_emploi.ods_import --download-pending
"""
from __future__ import annotations

import argparse
import shutil
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .config import CONFIG, CV_DIR
from .database import init_db
from . import repository as repo
from .scraper import download_annonce, is_http_url

DEFAULT_STATUS = CONFIG.get("default_status", "Candidature envoyée")
# Variante d'orthographe fréquente à normaliser vers le statut par défaut.
SOURCE_SENT_LABEL = "Candidature envoyé"


def _clean(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _parse_date(value) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def import_initial_cv(cv_path: Path) -> int | None:
    """Copie un fichier CV et l'enregistre comme CV actuel (fichier jamais lu)."""
    if not cv_path.exists():
        print(f"  ! CV introuvable : {cv_path}")
        return None
    stored = f"{uuid.uuid4().hex}{cv_path.suffix or '.pdf'}"
    shutil.copy2(cv_path, CV_DIR / stored)
    cv_id = repo.create_cv(
        name=cv_path.stem,
        stored_filename=stored,
        original_filename=cv_path.name,
        make_current=True,
    )
    print(f"  ✓ CV importé (id={cv_id})")
    return cv_id


def import_rows(cv_id: int | None, ods_path: Path) -> list[tuple[int, str]]:
    """Crée les candidatures et renvoie la liste (app_id, url) à télécharger."""
    df = pd.read_excel(ods_path, engine="odf", header=0)
    df.columns = ["num", "date", "offre", "entreprise", "url", "etat", "commentaire"][
        : len(df.columns)
    ]

    to_download: list[tuple[int, str]] = []
    created = 0

    for _, row in df.iterrows():
        applied = _parse_date(row.get("date"))
        title = _clean(row.get("offre"))
        if applied is None or not title:
            continue  # ligne inexploitable

        url = _clean(row.get("url"))
        company = _clean(row.get("entreprise"))
        etat = _clean(row.get("etat")) or DEFAULT_STATUS
        commentaire = _clean(row.get("commentaire"))
        downloadable = is_http_url(url)

        app_id = repo.create_application(
            applied_at=applied,
            title=title,
            company=company,
            url=url,
            cv_id=cv_id,
            is_downloadable_url=downloadable,
            initial_status=DEFAULT_STATUS,
        )
        created += 1

        # Statut supplémentaire (refus / entretien) + éventuel commentaire.
        if etat and etat not in (SOURCE_SENT_LABEL, DEFAULT_STATUS):
            comment_date = _parse_date(commentaire)
            if comment_date is not None:
                changed_at = datetime.combine(comment_date, datetime.min.time())
                repo.add_status_event(app_id, etat, changed_at=changed_at)
            else:
                # Pas de date exploitable : repli sur la date de candidature.
                changed_at = datetime.combine(applied, datetime.min.time())
                repo.add_status_event(app_id, etat, changed_at=changed_at)
                if commentaire:
                    repo.add_comment(app_id, commentaire)
        elif commentaire and _parse_date(commentaire) is None:
            # Statut par défaut mais commentaire texte présent.
            repo.add_comment(app_id, commentaire)

        if downloadable:
            to_download.append((app_id, url))

    print(f"  ✓ {created} candidature(s) importée(s)")
    return to_download


def download_all(targets: list[tuple[int, str]], workers: int = 8) -> None:
    """Télécharge les copies locales en parallèle, écrit les résultats séquentiellement."""
    if not targets:
        return
    print(f"  … téléchargement de {len(targets)} annonce(s) (best-effort)…")
    results: list[tuple[int, bool, str | None]] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(download_annonce, url, app_id): app_id
            for app_id, url in targets
        }
        for future in as_completed(futures):
            app_id = futures[future]
            try:
                ok, path, _msg = future.result()
            except Exception:  # noqa: BLE001 - best-effort
                ok, path = False, None
            results.append((app_id, ok, path))

    # Écriture séquentielle (évite les verrous SQLite).
    ok_count = 0
    for app_id, ok, path in results:
        repo.set_annonce_result(app_id, ok, path)
        ok_count += int(ok)
    print(f"  ✓ copies locales : {ok_count} réussie(s) / {len(targets)} tentée(s)")


def run_import(
    ods_path: Path,
    cv_path: Path | None = None,
    download: bool = True,
    force: bool = False,
) -> int:
    """Importe depuis `ods_path`. Renvoie 0 si succès, 1 si base non vide (sans --force)."""
    init_db()
    if repo.count_applications() > 0 and not force:
        print(
            "La base contient déjà des candidatures. "
            "Utilisez --force pour importer quand même (crée des doublons)."
        )
        return 1

    if not ods_path.exists():
        print(f"Fichier introuvable : {ods_path}")
        return 1

    print("Import en cours…")
    cv_id = import_initial_cv(cv_path) if cv_path else None
    targets = import_rows(cv_id, ods_path)
    if download:
        download_all(targets)
    print("Terminé.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Importe des candidatures depuis un tableur .ods."
    )
    parser.add_argument(
        "--file", type=Path, help="Chemin du tableur .ods à importer."
    )
    parser.add_argument(
        "--cv", type=Path, default=None,
        help="Chemin d'un fichier CV à enregistrer comme CV actuel (optionnel).",
    )
    parser.add_argument(
        "--force", action="store_true", help="Importe même si la base n'est pas vide."
    )
    parser.add_argument(
        "--no-download", action="store_true", help="N'effectue pas les téléchargements."
    )
    parser.add_argument(
        "--download-pending",
        action="store_true",
        help="N'importe rien ; (re)télécharge seulement les copies manquantes/échouées.",
    )
    args = parser.parse_args()

    init_db()

    if args.download_pending:
        download_all(repo.list_pending_annonces())
        print("Terminé.")
        return 0

    if not args.file:
        parser.error("--file est requis (ou utilisez --download-pending).")

    return run_import(
        ods_path=args.file, cv_path=args.cv,
        download=not args.no_download, force=args.force,
    )


if __name__ == "__main__":
    sys.exit(main())
