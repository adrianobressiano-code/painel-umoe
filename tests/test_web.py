import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from generator import history, parse, render, run, webscrape
from generator.model import Day
from generator.settings import load

S = load(Path(__file__).with_name("config_test.json"))
S.source = "web"
RAW = json.load(open(Path(__file__).with_name("fixtures") / "scrape_2026-10-08.json"))
D = date(2026, 10, 8)
KNOWN = {"2026-10-01": 56428, "2026-10-02": 266031, "2026-10-03": 15519, "2026-10-04": 0,
         "2026-10-05": 99825, "2026-10-06": 38121, "2026-10-07": 126391}


def test_num():
    assert parse.num("9.071") == 9071 and parse.num("-3.985") == -3985 and parse.num("(3.985)") == -3985
    assert parse.num("(Em branco)") == 0 and parse.num("") == 0 and parse.num(None) == 0 and parse.num("R$ 1.234") == 1234
    with pytest.raises(parse.ParseError):
        parse.num("abc")


def test_detail_row_with_and_without_exit_date():
    a = ["123052", "M", "CC", "886264", "07/10/2026 10:35:32", "90574", "BOMBA X", "1", "9.071"]
    b = ["114006", "M", "CC", "886005", "07/10/2026 07:43:00", "08/10/2026 09:24:07", "78105", "CAIXA Y", "2", "2.932"]
    assert parse.parse_detail_row(a)["code"] == "90574" and parse.parse_detail_row(a)["value"] == 9071
    r = parse.parse_detail_row(b)
    assert r["code"] == "78105" and r["desc"] == "CAIXA Y" and r["qty"] == 2 and r["value"] == 2932
    with pytest.raises(parse.ParseError):
        parse.parse_detail_row(["x"] * 5)


def test_parse_real_page_capture():
    day = parse.parse_day(RAW, D)
    assert day.total == 56183 and day.source_stamp == "08/10/26 18:00"
    assert day.classes[0] == ("Manutenção Oportunidade", 16585) and len(day.cost_centers) == 17  # zeros removidos
    assert day.fleet[0] == ("123062", "COLHEDORA JD CH 670", 9644) and day.fleet_partial
    assert day.materials[0]["value"] == 9071 and len(day.materials) == 10
    assert render.validate(day) == []
    parse.check_detail_sorted(RAW)


def test_wrong_date_filter_is_rejected():
    with pytest.raises(parse.ParseError):
        parse.parse_day(RAW, date(2026, 10, 7))


def test_missing_table_is_reported():
    raw = {k: v for k, v in RAW.items() if k != "fleet"}
    with pytest.raises(parse.ParseError, match="fleet"):
        parse.parse_day(raw, D)


def test_empty_day_blank_hero():
    day = parse.parse_day({"hero": "(Em branco)", "start": "04/10/2026", "end": "04/10/2026"}, date(2026, 10, 4))
    assert day.total == 0 and day.classes == []


def test_unsorted_detail_is_rejected():
    raw = {"detail": {"rows": [["a", "b", "c", "1", "01/10/2026 10:00:00", "9", "d", "1", "10"],
                               ["a", "b", "c", "1", "01/10/2026 10:00:00", "9", "d", "1", "20"]]}}
    with pytest.raises(parse.ParseError):
        parse.check_detail_sorted(raw)


def test_validate_partial_fleet_rules():
    day = parse.parse_day(RAW, D)
    day.fleet = day.fleet[:5]                       # so 5 linhas e soma != total -> suspeito
    assert any("frota" in e for e in render.validate(day))
    day = parse.parse_day(RAW, D)
    day.fleet = [("1", "X", 99999)] + day.fleet     # soma passa do total -> erro
    assert any("passa do total" in e for e in render.validate(day))


def test_days_to_read():
    month = dict(KNOWN)
    got = history.days_to_read(D, month, full=False)
    assert [d.day for d in got] == [5, 6, 7, 8]         # ultimos 3 dias + hoje (revisoes)
    assert len(history.days_to_read(D, month, full=True)) == 8
    assert [d.day for d in history.days_to_read(D, {"2026-10-07": 1}, False)] == [1, 2, 3, 4, 5, 6, 7, 8]


class FakeScraper:
    truth = dict(KNOWN, **{"2026-10-08": 56183})
    calls = []

    def __init__(self, url, log=print):
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def day(self, d, validator=None):
        FakeScraper.calls.append(("day", d))
        return parse.parse_day(dict(RAW, start=d.strftime("%d/%m/%Y"), end=d.strftime("%d/%m/%Y")), d)

    def total(self, a, b=None):
        FakeScraper.calls.append(("total", a, b))
        if b is None:
            return self.truth[a.isoformat()]
        return sum(v for k, v in self.truth.items() if a.isoformat() <= k <= b.isoformat())


@pytest.fixture
def web(monkeypatch, tmp_path):
    FakeScraper.calls = []
    FakeScraper.truth = dict(KNOWN, **{"2026-10-08": 56183})
    monkeypatch.setattr(webscrape, "Scraper", FakeScraper)
    monkeypatch.setattr(history, "PATH", tmp_path / "data" / "history.json")
    monkeypatch.setattr(run.settings, "load", lambda: S)
    S.public_url = "https://exemplo"
    return tmp_path


def test_run_web_first_time_reads_whole_month_and_saves_history(web):
    assert run.main(["--out", str(web / "site"), "--date", "2026-10-08"]) == 0
    html = (web / "site" / "index.html").read_text(encoding="utf8")
    assert "R$ 56.183" in html and "R$ 658.498" not in html.split("<script")[0]
    hist = json.loads((web / "data" / "history.json").read_text())
    assert hist["2026-10"]["2026-10-07"] == 126391 and hist["2026-10"]["2026-10-08"] == 56183
    assert sum(hist["2026-10"].values()) == 658498
    assert (web / "site" / "api" / "v1" / "month.json").exists()


def test_run_web_incremental_rereads_only_recent_days(web):
    history.save({"2026-10": dict(KNOWN)})
    FakeScraper.truth["2026-10-07"] = 126500   # dia revisado pelo Power BI
    assert run.main(["--out", str(web / "site"), "--date", "2026-10-08"]) == 0
    hist = history.load()
    assert hist["2026-10"]["2026-10-07"] == 126500                    # revisao capturada
    totals = [c for c in FakeScraper.calls if c[0] == "total" and c[2] is None]
    assert [c[1].day for c in totals] == [5, 6, 7]                    # nao relê 01-04


def test_run_web_old_day_revision_triggers_full_reread(web):
    history.save({"2026-10": dict(KNOWN)})
    FakeScraper.truth["2026-10-02"] = 270000                          # dia antigo revisado (fora da janela de 3 dias)
    assert run.main(["--out", str(web / "site"), "--date", "2026-10-08"]) == 0
    assert history.load()["2026-10"]["2026-10-02"] == 270000


def test_run_web_aborts_and_keeps_history_when_inconsistent(web, monkeypatch):
    history.save({"2026-10": dict(KNOWN)})
    before = (web / "data" / "history.json").read_text()
    orig = FakeScraper.total

    def liar(self, a, b=None):
        return orig(self, a, b) + (5000 if b is not None else 0)       # total do periodo nunca bate
    monkeypatch.setattr(FakeScraper, "total", liar)
    assert run.main(["--out", str(web / "site"), "--date", "2026-10-08"]) == 1
    assert not (web / "site" / "index.html").exists()
    assert (web / "data" / "history.json").read_text() == before


def test_run_web_new_month_starts_clean(web):
    FakeScraper.truth = {"2026-11-01": 56183}
    history.save({"2026-10": dict(KNOWN)})
    assert run.main(["--out", str(web / "site"), "--date", "2026-11-01"]) == 0
    h = history.load()
    assert h["2026-11"] == {"2026-11-01": 56183} and "2026-10" in h
    assert json.loads((web / "site/api/v1/month.json").read_text())["month"] == "2026-11"


def test_scraper_requires_url():
    with pytest.raises(parse.ParseError):
        webscrape.Scraper("")
