"""CLI de gestion de la base de données.

Deux façons de démarrer :

- Base **vide** (aucune donnée) :
    python -m assistant_emploi.manage init

- Import depuis un tableur ODS :
    python -m assistant_emploi.manage import-ods --file candidatures.ods [--cv CV.pdf]
                                                 [--no-download] [--force]

- Repartir de zéro (vide la base) :
    python -m assistant_emploi.manage reset [--force] [--drop-files]

Note : l'application crée aussi automatiquement une base vide au premier lancement
si aucune n'existe.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import repository as repo
from .database import create_empty_db, reset_db


def _cmd_init(_args: argparse.Namespace) -> int:
    create_empty_db()
    print("Base de données vide prête (tables + statuts par défaut).")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    # Import différé pour éviter de charger pandas/odfpy quand ce n'est pas utile.
    from .ods_import import run_import

    return run_import(
        ods_path=args.file,
        cv_path=args.cv,
        download=not args.no_download,
        force=args.force,
    )


def _cmd_reset(args: argparse.Namespace) -> int:
    if repo.count_applications() > 0 and not args.force:
        print(
            "La base contient des données. Relancez avec --force pour tout effacer."
        )
        return 1
    reset_db(drop_files=args.drop_files)
    print("Base réinitialisée (vide).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m assistant_emploi.manage",
        description="Gestion de la base de données de l'Assistant Emploi.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Créer une base vide (aucune donnée).")
    p_init.set_defaults(func=_cmd_init)

    p_import = sub.add_parser(
        "import-ods", help="Importer les candidatures depuis un tableur ODS."
    )
    p_import.add_argument(
        "--file", type=Path, required=True, help="Chemin du tableur .ods à importer."
    )
    p_import.add_argument(
        "--cv", type=Path, default=None,
        help="Chemin d'un fichier CV à enregistrer comme CV actuel (optionnel).",
    )
    p_import.add_argument(
        "--no-download", action="store_true",
        help="Ne pas télécharger les copies locales des annonces.",
    )
    p_import.add_argument(
        "--force", action="store_true",
        help="Importer même si la base contient déjà des candidatures.",
    )
    p_import.set_defaults(func=_cmd_import)

    p_reset = sub.add_parser("reset", help="Vider la base et recréer une base vide.")
    p_reset.add_argument(
        "--force", action="store_true", help="Confirmer l'effacement des données."
    )
    p_reset.add_argument(
        "--drop-files", action="store_true",
        help="Supprimer aussi le fichier SQLite sur le disque.",
    )
    p_reset.set_defaults(func=_cmd_reset)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
