#!/usr/bin/env python3
"""Converte o HTML do painel "Materiais Aplicados - UMOE" em arquivos JSON (a "API estatica").

Uso:  python3 build_api.py <dashboard.html> <pasta_saida>
Gera: <saida>/api/v1/index.json, today.json, month.json
So usa a biblioteca padrao. Falha (exit 1) se o HTML nao tiver a estrutura esperada,
para nunca publicar JSON errado.
"""
import html as htmllib, json, os, re, sys
from datetime import date, datetime

GAUGE_MAX = 58000
TZ = "-03:00"  # America/Sao_Paulo (sem horario de verao desde 2019)


def num(s):
    s = re.sub(r"[^\d,.\-]", "", s)
    s = s.replace(".", "").replace(",", ".")
    return int(round(float(s))) if s else 0


def text(s):
    return htmllib.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ").strip()


def clean(s):
    return re.sub(r"\s+", " ", text(s))


def section(h, title):
    m = re.search(r"<h2>\s*" + re.escape(title) + r"\s*</h2>(.*?)</section>", h, re.S)
    if not m:
        raise ValueError("secao nao encontrada: " + title)
    return m.group(1)


def is_empty(sec):
    return bool(re.search(r"Sem aplica|Nenhum lan", sec))


def bars(sec):
    """Retorna (itens, demais) de uma lista de barras."""
    items, others = [], None
    for m in re.finditer(r'<div class="barrow(?P<d> demais)?">\s*<span class="bname">(?P<n>.*?)</span>.*?<span class="bval[^"]*">(?P<v>.*?)</span>\s*</div>', sec, re.S):
        name, val = clean(m.group("n")), num(m.group("v"))
        if m.group("d"):
            others = val
        else:
            items.append({"name": name, "value": val})
    om = re.search(r'<div class="other">\s*Demais[^<]*?(?:R\$\s*)?([\d.]+)\s*</div>', sec)
    if om:
        others = num(om.group(1))
    return items, others


def split_fleet(name):
    m = re.match(r"^(\d+)\s*[·\-]\s*(.+)$", name)
    return (m.group(1), m.group(2)) if m else (None, name)


def parse_fleet(sec):
    if is_empty(sec):
        return [], None
    if "<table" in sec:
        items = []
        for tr in re.findall(r"<tr>(.*?)</tr>", sec, re.S):
            tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            if len(tds) >= 3:
                cls = "agg" in tr
                items.append((clean(tds[0]), clean(tds[1]), num(tds[2]), cls))
        out, others = [], None
        for code, model, val, agg in items:
            if agg:
                others = val
            else:
                out.append({"code": code, "model": model, "value": val})
        return out, others
    items, others = bars(sec)
    out = []
    for it in items:
        code, model = split_fleet(it["name"])
        out.append({"code": code, "model": model, "value": it["value"]})
    return out, others


def parse_materials(sec):
    if is_empty(sec):
        return []
    out = []
    for tr in re.findall(r"<tr>(.*?)</tr>", sec, re.S):
        tds = re.findall(r"<td([^>]*)>(.*?)</td>", tr, re.S)
        if len(tds) < 4:
            continue
        code = clean(tds[0][1])
        desc_html = tds[1][1]
        eq = re.search(r'<span class="eq">(.*?)</span>', desc_html, re.S)
        desc = clean(re.sub(r'<span class="eq">.*?</span>', "", desc_html, flags=re.S))
        equip = clean(eq.group(1)) if eq else ""
        parts = [p.strip() for p in equip.split("·")]
        eqc, eqm = None, equip
        if len(parts) == 2:  # aceita "123061 · Modelo" e "Modelo · 123061"
            if parts[0].isdigit():
                eqc, eqm = parts[0], parts[1]
            elif parts[1].isdigit():
                eqc, eqm = parts[1], parts[0]
        out.append({"code": code, "description": desc,
                    "equipment": {"code": eqc, "model": eqm},
                    "quantity": num(tds[2][1]), "value": num(tds[3][1])})
    return out


def parse(h):
    h = h[h.index("<title>"):] if "<title>" in h else h
    upd = re.search(r"atualizados em\s*<b>(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d)</b>", h)
    lab = re.search(r"materiais aplicados\s*[—-]\s*(\d\d)/(\d\d)/(\d{4})", h)
    hero = re.search(r'<p class="value mono">R\$\s*([\d.]+)</p>', h)
    md = re.search(r'<script id="month-data" type="application/json">(.*?)</script>', h, re.S)
    if not (upd and lab and hero and md):
        raise ValueError("cabecalho, data, valor ou month-data ausente")
    day = date(int(lab.group(3)), int(lab.group(2)), int(lab.group(1)))
    total = num(hero.group(1))
    month = json.loads(md.group(1))
    updated = datetime(int(upd.group(3)), int(upd.group(2)), int(upd.group(1)), int(upd.group(4)), int(upd.group(5)))

    cls_sec = section(h, "Por classe de manutenção")
    cc_sec = section(h, "Por centro de custo")
    fl_title = "Top 10 equipamentos (frota)" if "<h2>Top 10 equipamentos (frota)</h2>" in h else "Equipamentos (frota)"
    fl_sec = section(h, fl_title)
    mat_sec = section(h, "Materiais de maior valor")
    pt_sec = section(h, "Por tipo de peças/serviços")

    classes = [] if is_empty(cls_sec) else bars(cls_sec)[0]
    cc_items, cc_others = ([], None) if is_empty(cc_sec) else bars(cc_sec)
    fleet, fleet_others = parse_fleet(fl_sec)
    parts = [] if is_empty(pt_sec) else bars(pt_sec)[0]
    materials = parse_materials(mat_sec)

    checks = {
        "classesSumEqualsTotal": sum(i["value"] for i in classes) == total,
        "partsTypeSumEqualsTotal": sum(i["value"] for i in parts) == total,
        "costCentersSumEqualsTotal": (sum(i["value"] for i in cc_items) + (cc_others or 0)) == total,
        "fleetSumEqualsTotal": (sum(i["value"] for i in fleet) + (fleet_others or 0)) == total,
        "todayInMonthHistory": month["daily"].get(day.isoformat()) == total,
    }
    if total == 0:  # dia vazio: tudo zerado e consistente
        checks = {k: (v if k == "todayInMonthHistory" else True) for k, v in checks.items()}

    today = {
        "schemaVersion": 1,
        "date": day.isoformat(),
        "updatedAt": updated.isoformat() + TZ,
        "currency": "BRL",
        "hasData": total > 0,
        "total": total,
        "gauge": {"max": GAUGE_MAX, "percent": round(total / GAUGE_MAX * 100, 1)},
        "byMaintenanceClass": classes,
        "byCostCenter": {"items": cc_items, "others": cc_others if cc_items or cc_others else 0},
        "byFleet": {"items": fleet, "others": fleet_others if fleet or fleet_others else 0},
        "byPartsType": parts,
        "topMaterials": materials,
        "checks": checks,
    }

    days = sorted(month["daily"])
    run, daily = 0, []
    for d in days:
        run += month["daily"][d]
        daily.append({"date": d, "value": month["daily"][d], "cumulative": run})
    n = len(daily)
    best = max(daily, key=lambda x: x["value"]) if daily else None
    mjson = {
        "schemaVersion": 1,
        "month": month["month"],
        "updatedAt": updated.isoformat() + TZ,
        "currency": "BRL",
        "daysRecorded": n,
        "total": run,
        "dailyAverage": round(run / n, 2) if n else 0,
        "peakDay": {"date": best["date"], "value": best["value"]} if best else None,
        "daily": daily,
    }
    index = {
        "schemaVersion": 1,
        "name": "UMOE Bioenergy - Materiais Aplicados",
        "source": "Power BI 'Materiais Aplicados - Por Equipamento - UMOE' (API oficial do Power BI)",
        "timezone": "America/Sao_Paulo",
        "updatedAt": updated.isoformat() + TZ,
        "endpoints": {"today": "today.json", "month": "month.json"},
        "notes": "Valores em BRL, sem centavos. O dia corrente e parcial ate o fechamento; dias passados podem ser revisados pelo Power BI.",
    }
    return index, today, mjson


def main(src, out):
    h = open(src, encoding="utf8").read()
    index, today, month = parse(h)
    d = os.path.join(out, "api", "v1")
    os.makedirs(d, exist_ok=True)
    for name, obj in (("index.json", index), ("today.json", today), ("month.json", month)):
        with open(os.path.join(d, name), "w", encoding="utf8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
    bad = [k for k, v in today["checks"].items() if not v]
    print("ok", today["date"], today["total"], "checks_falhos=" + (",".join(bad) or "nenhum"))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as e:  # noqa
        print("ERRO:", e, file=sys.stderr)
        sys.exit(1)
