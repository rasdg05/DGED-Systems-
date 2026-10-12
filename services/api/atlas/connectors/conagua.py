import os
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

from atlas.connectors.http import fetch

SMN_XLSX = (
    "https://smn.conagua.gob.mx/tools/RESOURCES/"
    "Monitor%20de%20Sequia%20en%20Mexico/MunicipiosSequia.xlsx"
)
ARCGIS = "https://sigagis.conagua.gob.mx/ArcGIS/rest/services?f=pjson"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
EXCEL_EPOCH = datetime(1899, 12, 30)


def _cache_path():
    override = os.environ.get("ATLAS_CACHE")
    if override:
        root = Path(override)
    else:
        root = Path("/tmp/atlas-cache")
        for parent in Path(__file__).resolve().parents:
            if (parent / "ontology").is_dir():
                root = parent / ".cache"
                break
    root.mkdir(parents=True, exist_ok=True)
    return root / "MunicipiosSequia.xlsx"


def _column_index(letters):
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return index


def _load_rows(path):
    with zipfile.ZipFile(path) as workbook:
        shared = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
        strings = []
        for item in shared.findall(f"{NS}si"):
            strings.append("".join((node.text or "") for node in item.iter(f"{NS}t")))
        sheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        rows = sheet.findall(f"{NS}sheetData/{NS}row")

        def cells(row):
            values = {}
            for cell in row:
                ref = cell.attrib.get("r", "")
                match = re.match(r"([A-Z]+)", ref)
                if not match:
                    continue
                column = match.group(1)
                kind = cell.attrib.get("t")
                node = cell.find(f"{NS}v")
                if node is None or node.text is None:
                    continue
                values[column] = strings[int(node.text)] if kind == "s" else node.text
            return values

        header = cells(rows[0])
        date_columns = []
        for column, value in header.items():
            try:
                serial = float(value)
            except (TypeError, ValueError):
                continue
            if serial > 30000:
                date_columns.append(( _column_index(column), column, serial))
        date_columns.sort()
        file_as_of = None
        if date_columns:
            file_as_of = (EXCEL_EPOCH + timedelta(days=date_columns[-1][2])).date().isoformat()
        table = {}
        for row in rows[1:]:
            data = cells(row)
            key = str(data.get("A", "")).zfill(5)
            if not key.strip("0"):
                continue
            category = None
            as_of = None
            for _, column, serial in reversed(date_columns):
                raw = data.get(column)
                if raw is None or str(raw).strip() == "":
                    continue
                category = raw
                as_of = (EXCEL_EPOCH + timedelta(days=serial)).date().isoformat()
                break
            table[key] = {
                "cvegeo": key,
                "state_code": data.get("B"),
                "mun_code": data.get("C"),
                "name": data.get("D"),
                "state": data.get("E"),
                "basin_org": data.get("F"),
                "category": category,
                "as_of": as_of,
            }
        return {"as_of": file_as_of, "rows": len(table), "table": table}


def _is_xlsx(body):
    return bool(body) and body[:2] == b"PK"


def load_drought(force=False):
    path = _cache_path()
    if path.exists() and not _is_xlsx(path.read_bytes()[:2]):
        # Una página de error guardada como .xlsx tumbaba el arranque (2026-10-12).
        path.unlink()
    if force or not path.exists() or path.stat().st_size < 1000:
        result = fetch(SMN_XLSX, timeout=60)
        if result["ok"] and not _is_xlsx(result["body"]):
            # El SMN contesta 200 con una página HTML "This page can't be displayed" desde
            # algunos servidores. No es el libro: se reporta como falla y no se guarda.
            result = dict(result, ok=False, error=f"HTTP {result['status']} {result.get('content_type') or ''}: no es un xlsx".strip())
        if not result["ok"]:
            if path.exists():
                loaded = _load_rows(path)
                loaded["stale"] = True
                loaded["error"] = result.get("error")
                loaded["url"] = SMN_XLSX
                return loaded
            return {
                "ok": False,
                "url": SMN_XLSX,
                "error": result.get("error") or f"HTTP {result['status']}",
                "table": {},
            }
        path.write_bytes(result["body"])
    loaded = _load_rows(path)
    loaded["ok"] = True
    loaded["url"] = SMN_XLSX
    loaded["bytes"] = path.stat().st_size
    return loaded


def probe_arcgis():
    # El REST público de SIGA a veces entra en redirección infinita. Se reporta, no se disimula.
    result = fetch(ARCGIS, timeout=12)
    body = result["body"][:180].decode("utf-8", "replace")
    loop = "maximum" in (result.get("error") or "").lower() or result["status"] in (301, 302)
    return {
        "source": "conagua.arcgis",
        "url": ARCGIS,
        "ok": result["ok"] and result["body"][:1] in (b"{", b"["),
        "status": result["status"],
        "error": result.get("error"),
        "excerpt": body,
        "redirect_loop": (not result["ok"]) and result["status"] in (0, 301, 302),
        "note": (
            "El catálogo ArcGIS de sigagis.conagua.gob.mx no entregó JSON. "
            "La sequía entra por el libro oficial del SMN, que sí responde."
            if loop or not result["ok"]
            else "Catálogo ArcGIS respondió."
        ),
    }
