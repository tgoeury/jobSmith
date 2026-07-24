"""Export des candidatures au format OpenDocument Spreadsheet (.ods)."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableCell, TableRow
from odf.text import P

from .config import EXPORTS_DIR
from .repository import list_all_applications

COLUMNS = ["Date", "Poste", "Entreprise", "Dernier statut", "URL"]


def _cell(value: str) -> TableCell:
    cell = TableCell(valuetype="string")
    cell.addElement(P(text=value if value is not None else ""))
    return cell


def _fmt_date(value) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value or "")


def export_applications_ods(path: Path | None = None) -> Path:
    """Génère un .ods listant toutes les candidatures. Renvoie le chemin du fichier."""
    if path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = EXPORTS_DIR / f"export_candidatures_{stamp}.ods"

    doc = OpenDocumentSpreadsheet()
    table = Table(name="Candidatures")

    header = TableRow()
    for col in COLUMNS:
        header.addElement(_cell(col))
    table.addElement(header)

    for app in list_all_applications():
        row = TableRow()
        row.addElement(_cell(_fmt_date(app["applied_at"])))
        row.addElement(_cell(app["title"]))
        row.addElement(_cell(app["company"] or ""))
        row.addElement(_cell(app["current_status"] or ""))
        row.addElement(_cell(app["url"] or ""))
        table.addElement(row)

    doc.spreadsheet.addElement(table)
    doc.save(str(path))
    return path
