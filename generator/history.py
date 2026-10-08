"""Historico diario do mes (data/history.json) e logica de quais dias reler."""
import json
from datetime import date, timedelta
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "history.json"


def load(path: Path | None = None) -> dict:
    try:
        return json.loads((path or PATH).read_text(encoding="utf8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(hist: dict, path: Path | None = None):
    path = path or PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hist, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf8")


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def iso(d: date) -> str:
    return d.isoformat()


def days_to_read(today: date, month: dict, full: bool, recent: int = 3) -> list[date]:
    """Dias do mes (1..hoje) que precisam ser lidos: faltantes, os ultimos `recent` (revisoes) ou todos (full)."""
    first = today.replace(day=1)
    allm = [first + timedelta(days=i) for i in range((today - first).days + 1)]
    if full:
        return allm
    out = []
    for d in allm:
        if iso(d) not in month or (today - d).days <= recent:
            out.append(d)
    return out
