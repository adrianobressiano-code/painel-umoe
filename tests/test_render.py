import json
import re
from datetime import date

import pytest

from generator import apijson, model, render
from generator.settings import load
from tests.day_0810 import MONTH, day_0810

from pathlib import Path
S = load(Path(__file__).with_name('config_test.json'))
NOW = "08/10/2026 11:42"
FIX = open("tests/fixtures/dashboard_2026-10-08.html", encoding="utf8").read()


def norm(h):
    h = re.sub(r"data:image[^\"]+", "DATA", h)
    h = re.sub(r'<div class="src">.*?</div>', "SRC", h, flags=re.S)
    h = re.sub(r"<div>(Gerado por Claude|Atualizado automaticamente) · [^<]*</div>", "STAMP", h)
    h = re.sub(r'"updatedAt": "[^"]*"', '"updatedAt": "X"', h)
    return re.sub(r"\s+", " ", h)


def test_matches_manually_published_dashboard():
    """O gerador automatico reproduz EXATAMENTE o painel que eu publiquei a mao em 08/10 (mesmos numeros/HTML)."""
    out = render.render_fragment(day_0810(), MONTH, NOW, S)
    assert norm(out).strip() == norm(FIX.split("</title>", 1)[-1]).strip()


def test_validate_ok_and_detects_mismatch():
    d = day_0810()
    assert render.validate(d) == []
    d.classes = d.classes[:-1]
    assert any("classes" in e for e in render.validate(d))


def test_demais_by_subtraction_and_titles():
    cc, fl, title = render.sections(day_0810(), S)
    assert cc[-1] == ("Demais centros de custo", 706, True)
    assert fl[-1] == ("Demais equipamentos", 2490, True) and title == "Top 10 equipamentos (frota)"
    d = day_0810(); d.fleet = d.fleet[:5]
    _, fl2, t2 = render.sections(d, S)
    assert t2 == "Equipamentos (frota)" and not any(x[2] for x in fl2)


def test_empty_day():
    d = model.Day(date=date(2026, 10, 4))
    h = render.render_fragment(d, {"2026-10-04": 0}, NOW, S)
    assert 'stroke-dasharray="0 340"' in h and "R$ 0" in h
    assert h.count("Sem aplicações registradas em 04/10/2026 até o momento.") == 5
    assert "Equipamentos (frota)</h2>" in h and "Top 10 equipamentos" not in h


def test_above_scale_gauge():
    h = render.render_fragment(day_0810(), MONTH, NOW, S)
    assert 'stroke-dasharray="248 92"' in h and ">73%<" in h
    d = day_0810(); d.total = 70000
    h = render.render_fragment(d, MONTH, NOW, S)
    assert 'stroke-dasharray="339 1"' in h and "acima da escala" in h and 'font-size="15"' in h


def test_negative_values_render():
    d = day_0810()
    d.cost_centers = d.cost_centers[:3] + [("Credito", -400)]
    h = render.render_fragment(d, MONTH, NOW, S)
    assert "-R$ 400" in h and "width:-" not in h


def test_title_case_codes_and_acronyms():
    k = S.keep_upper
    assert render.title_case("CM VOLVO VM 270 6X4R", k) == "CM Volvo VM 270 6X4R"
    assert render.title_case("COLHEDORA JD CH 670", k) == "Colhedora JD CH 670"
    assert render.title_case('DISCO 30" 7 FACAS JOHN DEERE/CASE', k) == 'Disco 30" 7 Facas John Deere/Case'


def test_month_json_valid_and_api_parses():
    page = render.render_page(day_0810(), MONTH, NOW, S)
    m = re.search(r'<script id="month-data"[^>]*>(.*?)</script>', page, re.S)
    data = json.loads(m.group(1))
    assert sum(data["daily"].values()) == 644760 and data["month"] == "2026-10"
    index, today, month = apijson.parse(page)
    assert today["total"] == 42445 and all(today["checks"].values()) and month["total"] == 644760
    assert "<title>Materiais Aplicados" in page and page.startswith("<!doctype html>")
