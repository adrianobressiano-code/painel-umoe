"""Ciclo completo: le o Power BI, valida, gera site/index.html + site/api/v1/*.json.

Uso:  python -m generator.run [--out site] [--date AAAA-MM-DD] [--full]
Se QUALQUER verificacao falhar, sai com erro e NAO gera nada -> o site anterior continua no ar.
Fonte dos dados (config.json "source"): "web" (link publico, padrao) ou "api" (API oficial do Power BI).
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import apijson, history, model, render, settings


def log(*a):
    print(*a, flush=True)


def collect_api(s, today, full):
    day = model.fetch_day(s, today)
    errs = render.validate(day)
    month = model.fetch_month(s, today)
    if abs(month.get(today.isoformat(), 0) - day.total) > 1:
        errs.append(f"total do dia ({day.total}) difere do historico do mes ({month.get(today.isoformat())})")
    return day, month, errs, None


def collect_web(s, today, full, scraper_cls=None):
    """Le o dia de hoje (completo) + totais dos outros dias do mes; confere o mes contra o total do periodo."""
    from .webscrape import Scraper

    hist = history.load()
    mk, iso = history.month_key(today), today.isoformat()
    month = dict(hist.get(mk, {}))
    first = today.replace(day=1)
    with (scraper_cls or Scraper)(s.public_url, log=log) as sc:
        log(f"lendo {today:%d/%m/%Y} ...")
        try:
            day = sc.day(today, validator=render.validate)
        except Exception as e:   # leitura invalida: nao publica nada
            return model.Day(date=today), month, [f"{type(e).__name__}: {e}"], None
        errs = render.validate(day)
        month[iso] = day.total

        def read_days(full_pass):
            for d in history.days_to_read(today, month, full_pass):
                if d != today:
                    month[d.isoformat()] = sc.total(d)
                    log(f"  {d:%d/%m}: R$ {month[d.isoformat()]}")

        read_days(full)
        n = (today - first).days + 1
        tol = max(2, n // 2 + 1)
        span = sc.total(first, today)
        if abs(sum(month.values()) - span) > tol and not full:
            log(f"historico ({sum(month.values())}) difere do periodo ({span}); relendo o mes inteiro")
            read_days(True)
            month[iso] = day.total
        if abs(sum(month.values()) - span) > tol:
            errs.append(f"soma dos dias ({sum(month.values())}) difere do total do periodo {first:%d/%m}-{today:%d/%m} ({span})")
        if sc.day(today, validator=render.validate).total != day.total:   # o periodo mudou a pagina; confirma que o dia de hoje continua igual
            errs.append("o total de hoje mudou durante a leitura; tente de novo")
    # so guarda o historico do mes se tudo bateu
    hist[mk] = {k: month[k] for k in sorted(month)}
    for old in sorted(hist)[:-13]:
        hist.pop(old)
    return day, month, errs, hist


def main(argv=None, collect=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    ap.add_argument("--date", default="")  # so para testes manuais
    ap.add_argument("--full", action="store_true", help="reler todos os dias do mes")
    a = ap.parse_args(argv)
    s = settings.load()
    now = datetime.now(ZoneInfo(s.timezone))
    today = datetime.strptime(a.date, "%Y-%m-%d").date() if a.date else now.date()
    now_s = now.strftime("%d/%m/%Y %H:%M")
    full = a.full or os.environ.get("FULL_REFRESH") == "1"
    collect = collect or (collect_web if s.source == "web" else collect_api)

    try:
        day, month, errs, hist = collect(s, today, full)
    except Exception as e:  # qualquer falha de leitura: nao publica, o site anterior continua no ar
        log(f"ERRO ao ler o Power BI - nada foi publicado: {type(e).__name__}: {e}")
        return 1
    iso = today.isoformat()
    if not errs and sorted(month)[-1] != iso:
        errs.append("historico do mes sem o dia de hoje")
    if errs:
        log("ERRO de consistencia - nada foi publicado:\n  " + "\n  ".join(errs))
        return 1
    month[iso] = day.total

    page = render.render_page(day, month, now_s, s)
    index, today_j, month_j = apijson.parse(page)
    bad = [k for k, v in today_j["checks"].items() if not v and day.total > 0]
    # a frota pode ser parcial (so as 20 maiores): essa verificacao especifica nao se aplica
    bad = [k for k in bad if not (k == "fleetSumEqualsTotal" and day.fleet_partial)]
    if bad:
        log("ERRO: verificacoes do JSON falharam: " + ",".join(bad))
        return 1

    out = Path(a.out)
    (out / "api" / "v1").mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf8")
    for name, obj in (("index.json", index), ("today.json", today_j), ("month.json", month_j)):
        (out / "api" / "v1" / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    if hist is not None:
        history.save(hist)
    log(f"ok {iso} total=R$ {day.total:,} mes=R$ {sum(month.values()):,} gerado={now_s}".replace(",", "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
