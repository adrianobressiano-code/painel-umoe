"""Busca no Power BI os dados de um dia e o historico diario do mes."""
import calendar
from dataclasses import dataclass, field
from datetime import date

from . import pbi


@dataclass
class Day:
    date: date
    total: int = 0
    classes: list = field(default_factory=list)       # [(nome, valor)] decrescente, so nao-zero
    cost_centers: list = field(default_factory=list)  # [(nome, valor)]
    fleet: list = field(default_factory=list)         # [(codigo, modelo, valor)]
    parts: list = field(default_factory=list)         # [(nome, valor)]
    materials: list = field(default_factory=list)     # [dict(code, desc, qty, value, fleet, model)]
    fleet_partial: bool = False   # o visual de frota do relatorio so mostra as 20 maiores linhas
    source_stamp: str = ""        # carimbo 'dd/mm/aa hh:mm' da base do Power BI


def _i(v) -> int:
    return int(round(v or 0))


def _pairs(rows, key_col):
    out = [(str(pbi.col(r, key_col)), _i(pbi.col(r, "Total"))) for r in rows]
    return sorted([p for p in out if p[1] != 0], key=lambda p: -p[1])


def fetch_day(s, d: date) -> Day:
    rows = pbi.execute_queries(pbi.dax_total_day(s, d), s)
    total = _i(pbi.col(rows[0], "Total")) if rows else 0
    day = Day(date=d, total=total)
    if total == 0:
        return day
    run = lambda dax: pbi.execute_queries(dax, s)
    day.classes = _pairs(run(pbi.dax_group(s, d, ["class"])), s.c("class"))
    day.cost_centers = _pairs(run(pbi.dax_group(s, d, ["cost_center"])), s.c("cost_center"))
    day.parts = _pairs(run(pbi.dax_group(s, d, ["parts_type"])), s.c("parts_type"))
    fl = [(str(pbi.col(r, s.c("fleet"))), str(pbi.col(r, s.c("model"))), _i(pbi.col(r, "Total")))
          for r in run(pbi.dax_group(s, d, ["fleet", "model"]))]
    day.fleet = sorted([f for f in fl if f[2] != 0], key=lambda f: -f[2])
    for r in run(pbi.dax_materials(s, d)):
        day.materials.append({
            "code": str(pbi.col(r, s.c("material_code"))), "desc": str(pbi.col(r, s.c("material_desc"))),
            "qty": _i(pbi.col(r, "Qtd")), "value": _i(pbi.col(r, "Total")),
            "fleet": str(pbi.col(r, s.c("fleet"))), "model": str(pbi.col(r, s.c("model")))})
    day.materials.sort(key=lambda m: -m["value"])
    return day


def fetch_month(s, today: date) -> dict:
    """{'AAAA-MM-DD': total} de 01 ate hoje; dias sem lancamento = 0 (e hoje sempre presente)."""
    rows = pbi.execute_queries(pbi.dax_daily(s, today.year, today.month), s)
    got = {}
    for r in rows:
        raw = pbi.col(r, s.c("date"))
        if raw:
            got[str(raw)[:10]] = got.get(str(raw)[:10], 0) + _i(pbi.col(r, "Total"))
    out = {}
    for n in range(1, today.day + 1):
        k = f"{today.year:04d}-{today.month:02d}-{n:02d}"
        out[k] = got.get(k, 0)
    return out
