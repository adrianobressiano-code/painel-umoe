"""Converte as linhas cruas lidas da pagina (scrape_extract.js) em um Day. Funcoes puras (testaveis)."""
import re
from datetime import date

from .model import Day

DT = re.compile(r"^\d\d/\d\d/\d{4}( \d\d:\d\d(:\d\d)?)?$")


class ParseError(RuntimeError):
    pass


def num(text) -> int:
    """'9.071' -> 9071 ; '-3.985' / '(3.985)' -> -3985 ; '(Em branco)', '', None -> 0."""
    if text is None:
        return 0
    t = str(text).strip()
    if not t or t.lower().startswith("(em branc"):
        return 0
    neg = t.startswith("-") or (t.startswith("(") and t.endswith(")"))
    digits = re.sub(r"[^\d,]", "", t).replace(",", ".")
    if not digits:
        raise ParseError(f"numero ilegivel: {text!r}")
    v = int(round(float(digits)))
    return -v if neg else v


def _need(raw: dict, key: str):
    if key not in raw or not raw[key]["rows"]:
        raise ParseError(f"tabela '{key}' nao encontrada na pagina (o layout do relatorio mudou?)")
    return raw[key]["rows"]


def parse_detail_row(t: list[str]) -> dict:
    """[frota, modelo, centro, OS, entrada, (saida), codigo, descricao..., qtd, valor]"""
    if len(t) < 9:
        raise ParseError(f"linha de detalhamento curta: {t}")
    i = 4
    if not DT.match(t[i]):
        raise ParseError(f"data de entrada esperada: {t}")
    i += 1
    if DT.match(t[i]):  # data de saida (opcional)
        i += 1
    return {"fleet": t[0], "model": t[1], "cost_center": t[2], "os": t[3], "code": t[i],
            "desc": " ".join(t[i + 1:-2]), "qty": num(t[-2]), "value": num(t[-1])}


def parse_day(raw: dict, d: date) -> Day:
    want = d.strftime("%d/%m/%Y")
    if raw.get("start") != want or raw.get("end") != want:
        raise ParseError(f"filtro de data fora do esperado: {raw.get('start')}..{raw.get('end')} (queria {want})")
    total = num(raw.get("hero"))
    day = Day(date=d, total=total, fleet_partial=True, source_stamp=raw.get("stamp") or "")
    if total == 0:
        return day
    pairs = lambda key: sorted([(r[0], num(r[1])) for r in _need(raw, key) if len(r) == 2 and num(r[1]) != 0],
                               key=lambda p: -p[1])
    day.classes = pairs("classes")
    day.cost_centers = pairs("cost_centers")
    day.parts = pairs("parts")
    fl = []
    for r in _need(raw, "fleet"):
        if len(r) != 3:
            raise ParseError(f"linha de frota inesperada: {r}")
        if num(r[2]) != 0:
            fl.append((r[0], r[1], num(r[2])))
    day.fleet = sorted(fl, key=lambda f: -f[2])
    mats = [parse_detail_row(r) for r in _need(raw, "detail")]
    # mesmo item/OS pode aparecer em linhas separadas no relatorio; o relatorio ja traz ordenado por valor
    day.materials = sorted(mats, key=lambda m: -m["value"])
    return day


def check_detail_sorted(raw: dict):
    """O detalhamento precisa vir ordenado por valor (so lemos as primeiras linhas)."""
    vals = [num(r[-1]) for r in raw.get("detail", {}).get("rows", [])]
    if any(a < b for a, b in zip(vals, vals[1:])):
        raise ParseError("detalhamento nao esta ordenado por valor decrescente")
