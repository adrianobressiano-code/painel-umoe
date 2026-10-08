from datetime import date

import pytest

from generator import model, pbi, render, run
from generator.settings import load
from tests.day_0810 import FLEET, MATS, MONTH, day_0810

from pathlib import Path
S = load(Path(__file__).with_name('config_test.json'))
S.source = "api"
D = date(2026, 10, 8)


def test_dax_quoting_and_dates():
    S2 = load(Path(__file__).with_name("config_test.json")); S2.table = "Mat's"
    dax = pbi.dax_group(S2, D, ["class"])
    assert "'Mat''s'[Classe Manutenção]" in dax and "DATE(2026,10,8)" in dax and "ORDER BY [Total] DESC" in dax
    assert "TOPN(10" in pbi.dax_materials(S, D) and "'Materiais'[O.S]" in pbi.dax_materials(S, D)
    assert "YEAR('Materiais'[Data Aplicação.]) = 2026" in pbi.dax_daily(S, 2026, 10)
    S2.value_expr = "[Valor Total]"
    assert '"Total", [Valor Total]' in pbi.dax_group(S2, D, ["class"])


def test_col_strips_table_prefix():
    assert pbi.col({"Mat[Classe]": "A", "[Total]": 5}, "Classe") == "A"
    assert pbi.col({"Mat[Classe]": "A", "[Total]": 5}, "Total") == 5


def fake_factory(total=42445):
    d = day_0810()

    def fake(dax, s, retries=3):
        t = "'Materiais'"
        if dax.startswith("EVALUATE ROW"):
            return [{"[Total]": float(total)}]
        if "TOPN" in dax:
            return [{f"{t}[O.S]": "1", f"{t}[Cód.]": m["code"], f"{t}[Descrição Material]": m["desc"],
                     f"{t}[Frota]": m["fleet"], f"{t}[Modelo]": m["model"], "[Qtd]": m["qty"], "[Total]": m["value"] + 0.3}
                    for m in d.materials]
        if "YEAR(" in dax:
            return [{f"{t}[Data Aplicação.]": k + "T00:00:00", "[Total]": v + 0.2} for k, v in MONTH.items() if v]
        if "[Frota], 'Materiais'[Modelo]" in dax:
            return [{f"{t}[Frota]": c, f"{t}[Modelo]": m, "[Total]": v} for c, m, v in d.fleet]
        for key, items in (("Classe Manutenção", d.classes), ("Centro Custo", d.cost_centers), ("Tipo Peças/Serviços", d.parts)):
            if key in dax:
                return [{f"{t}[{key}]": n, "[Total]": v} for n, v in items]
        raise AssertionError(dax)
    return fake


def test_fetch_day_and_month(monkeypatch):
    monkeypatch.setattr(pbi, "execute_queries", fake_factory())
    day = model.fetch_day(S, D)
    assert day.total == 42445 and day.classes[0] == ("Manutenção Oportunidade", 11013)
    assert day.fleet[0][0] == "123052" and len(day.materials) == 10 and day.materials[0]["value"] == 9071
    month = model.fetch_month(S, D)
    assert list(month)[0] == "2026-10-01" and month["2026-10-04"] == 0 and month["2026-10-07"] == 126391


def test_empty_day_makes_no_extra_queries(monkeypatch):
    calls = []
    monkeypatch.setattr(pbi, "execute_queries", lambda dax, s, retries=3: calls.append(dax) or [{"[Total]": None}])
    day = model.fetch_day(S, D)
    assert day.total == 0 and len(calls) == 1


def test_run_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(pbi, "execute_queries", fake_factory())
    monkeypatch.setattr(run.settings, "load", lambda: S)
    assert run.main(["--out", str(tmp_path), "--date", "2026-10-08"]) == 0
    html = (tmp_path / "index.html").read_text(encoding="utf8")
    assert "R$ 42.445" in html and (tmp_path / "api/v1/today.json").exists()


def test_run_aborts_on_inconsistent_data(monkeypatch, tmp_path):
    f = fake_factory()
    # Power BI devolvendo uma classe a menos -> soma nao bate -> NAO pode publicar
    def broken(dax, s, retries=3):
        rows = f(dax, s)
        return rows[:-1] if "Classe Manutenção" in dax and "TOPN" not in dax else rows
    monkeypatch.setattr(pbi, "execute_queries", broken)
    monkeypatch.setattr(run.settings, "load", lambda: S)
    assert run.main(["--out", str(tmp_path / "o"), "--date", "2026-10-08"]) == 1
    assert not (tmp_path / "o" / "index.html").exists()


def test_run_aborts_when_month_history_disagrees(monkeypatch, tmp_path):
    monkeypatch.setattr(pbi, "execute_queries", fake_factory(total=40000))
    monkeypatch.setattr(run.settings, "load", lambda: S)
    assert run.main(["--out", str(tmp_path / "o"), "--date", "2026-10-08"]) == 1
