"""Monta o HTML do painel a partir dos dados (mesmo layout publicado manualmente)."""
import json
import re
from datetime import date
from pathlib import Path

TEMPLATE = Path(__file__).with_name("template.html")
MONTHS_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
             "setembro", "outubro", "novembro", "dezembro"]


def brl(n: int) -> str:
    return ("-" if n < 0 else "") + "R$ " + f"{abs(n):,}".replace(",", ".")


def num(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


def title_case(text: str, keep_upper) -> str:
    """CAIXA ALTA do Power BI -> Title Case legivel, mantendo codigos tecnicos (com digito) e siglas."""
    keep = {k.upper() for k in keep_upper}

    def fix(m):
        w = m.group(0)
        if any(ch.isdigit() for ch in w) or w.upper() in keep:
            return w.upper()
        return w[:1].upper() + w[1:].lower()

    return re.sub(r"[^\W\d_]+[\w]*|\w+", fix, text.strip())


def _row(name, val, mx, demais=False):
    w = max(0, int(round(val / mx * 100))) if mx > 0 else 0
    cls = "barrow demais" if demais else "barrow"
    return (f'          <div class="{cls}">\n            <span class="bname">{esc(name)}</span>\n'
            f'            <div class="btrack"><div class="bfill" style="width:{w}%"></div></div>\n'
            f'            <span class="bval mono">{brl(val)}</span>\n          </div>\n')


def _barlist(rows, extra=""):
    mx = max([v for _, v, d in rows if not d] or [1])
    return '<div class="barlist">\n' + "".join(_row(n, v, mx, d) for n, v, d in rows) + extra + "        </div>\n      "


def _empty(date_s, extra=""):
    return ('<div class="barlist"><div class="other" style="border-top:none;margin-top:0">'
            f"Sem aplicações registradas em {date_s} até o momento.</div>{extra}</div>\n      ")


def _section(h, titles, new_title, hint, inner):
    alt = "|".join(re.escape(t) for t in titles)
    pat = re.compile(r"<h2>(?:" + alt + r")</h2>\s*<p class=\"hint\">.*?</p>\s*.*?</section>", re.S)
    assert pat.search(h), titles
    block = f'<h2>{new_title}</h2>\n        <p class="hint">{hint}</p>\n        {inner}</section>'
    return pat.sub(lambda m: block, h, count=1)


def sections(day, s):
    """Devolve as listas ja recortadas (top-N + 'Demais' por SUBTRACAO do total)."""
    t = day.total
    cc = list(day.cost_centers)
    if len(cc) > 8:
        head = cc[:8]
        cc_rows = [(n, v, False) for n, v in head] + [("Demais centros de custo", t - sum(v for _, v in head), True)]
    else:
        cc_rows = [(n, v, False) for n, v in cc]
    fl = [(f"{c} · {title_case(m, s.keep_upper)}", v) for c, m, v in day.fleet]
    if len(fl) > 10:
        head = fl[:10]
        fl_rows = [(n, v, False) for n, v in head] + [("Demais equipamentos", t - sum(v for _, v in head), True)]
        fl_title = "Top 10 equipamentos (frota)"
    else:
        fl_rows = [(n, v, False) for n, v in fl]
        fl_title = "Equipamentos (frota)"
    return cc_rows, fl_rows, fl_title


def validate(day, tol_extra: int = 0):
    """Confere se as secoes somam ao total do dia (tolerancia = arredondamento por linha).

    Listas completas (classes, centros de custo, tipo de peca) precisam SOMAR o total.
    A frota pode ser parcial (o visual mostra so as 20 maiores): entao a soma nunca pode passar do total
    e precisamos de pelo menos 10 linhas (ou a soma bater o total)."""
    errs = []

    def tol(n):
        return max(2, n) + tol_extra

    for name, items in (("classes", [v for _, v in day.classes]), ("centros de custo", [v for _, v in day.cost_centers]),
                        ("tipo peças", [v for _, v in day.parts])):
        if day.total and abs(sum(items) - day.total) > tol(len(items)):
            errs.append(f"{name}: soma {sum(items)} != total {day.total}")
    fl = [v for *_, v in day.fleet]
    if day.total:
        diff = day.total - sum(fl)
        if day.fleet_partial:
            if diff < -tol(len(fl)):
                errs.append(f"frota: soma {sum(fl)} passa do total {day.total}")
            elif len(fl) < 10 and abs(diff) > tol(len(fl)):
                errs.append(f"frota: so {len(fl)} linhas e soma {sum(fl)} != total {day.total}")
        elif abs(diff) > tol(len(fl)):
            errs.append(f"frota: soma {sum(fl)} != total {day.total}")
    if day.total and not day.materials:
        errs.append("sem detalhamento de materiais")
    return errs


def render_fragment(day, month_daily: dict, now_s: str, s, template: str | None = None) -> str:
    h = template if template is not None else TEMPLATE.read_text(encoding="utf8")
    D = day.date.strftime("%d/%m/%Y")
    T = day.total
    cc_rows, fl_rows, fl_title = sections(day, s)

    if T == 0:
        h = _section(h, ["Por classe de manutenção"], "Por classe de manutenção",
                     f"Valor aplicado, por tipo de manutenção em {D}", _empty(D))
        h = _section(h, ["Por centro de custo"], "Por centro de custo",
                     f"Valor aplicado, por centro de custo em {D}", _empty(D))
        h = _section(h, ["Top 10 equipamentos (frota)", "Equipamentos (frota)"],
                     "Equipamentos (frota)", f"Valor aplicado, por equipamento em {D}", _empty(D))
        h = _section(h, ["Materiais de maior valor"], "Materiais de maior valor",
                      "Top 10 itens do detalhamento do dia", _empty(D))
        h = _section(h, ["Por tipo de peças/serviços"], "Por tipo de peças/serviços",
                     f"Valor aplicado, por tipo de peças/serviços em {D}",
                     _empty(D, '<div class="other">Total do dia: R$ 0</div>'))
    else:
        h = _section(h, ["Por classe de manutenção"], "Por classe de manutenção",
                     f"Valor aplicado, por tipo de manutenção em {D}",
                     _barlist([(n, v, False) for n, v in day.classes]))
        h = _section(h, ["Por centro de custo"], "Por centro de custo",
                     f"Valor aplicado, por centro de custo em {D}", _barlist(cc_rows))
        h = _section(h, ["Top 10 equipamentos (frota)", "Equipamentos (frota)"], fl_title,
                     f"Valor aplicado, por equipamento em {D}", _barlist(fl_rows))
        trs = ""
        for m in day.materials[:10]:
            eq = f"{m['fleet']} · {title_case(m['model'], s.keep_upper)}"
            trs += ('              <tr>\n'
                    f'                <td class="code">{esc(m["code"])}</td>\n'
                    f'                <td class="desc">{esc(title_case(m["desc"], s.keep_upper))}<span class="eq">{esc(eq)}</span></td>\n'
                    f'                <td class="num">{num(m["qty"])}</td>\n'
                    f'                <td class="num mono">{brl(m["value"])}</td>\n'
                    '              </tr>\n')
        table = ('<div class="tablewrap">\n          <table>\n            <thead>\n'
                 '              <tr><th>Cód.</th><th>Descrição</th><th>Qtd.</th><th>Valor</th></tr>\n'
                 '            </thead>\n            <tbody>\n' + trs +
                 '            </tbody>\n          </table>\n        </div>\n      ')
        h = _section(h, ["Materiais de maior valor"], "Materiais de maior valor",
                     "Top 10 itens do detalhamento do dia", table)
        h = _section(h, ["Por tipo de peças/serviços"], "Por tipo de peças/serviços",
                     f"Valor aplicado, por tipo de peças/serviços em {D}",
                     _barlist([(n, v, False) for n, v in day.parts],
                              extra=f'        <div class="other">Total do dia: {brl(T)}</div>\n'))

    # topo, hero, gauge
    def sub1(pat, repl, text):
        out, n = re.subn(pat, repl, text, flags=re.S)
        assert n == 1, pat
        return out

    h = sub1(r"(atualizados em <b>)[^<]*(</b>)", lambda m: m.group(1) + now_s + m.group(2), h)
    h = sub1(r"(Valor total de materiais aplicados — )\d\d/\d\d/\d{4}", lambda m: m.group(1) + D, h)
    h = sub1(r'(<p class="value mono">)[^<]*(</p>)', lambda m: m.group(1) + brl(T) + m.group(2), h)
    gmax = s.gauge_max
    if T > gmax:
        dash, big, fs, small = (339, 1), num(T), 15, "acima da escala"
    else:
        d1 = round(T / gmax * 339.292) if T > 0 else 0
        dash, big, fs, small = (d1, 340 - d1), num(max(T, 0)), 20, f"{round(max(T, 0) / gmax * 100)}%"
    h = sub1(r'stroke-dasharray="[^"]*"', f'stroke-dasharray="{dash[0]} {dash[1]}"', h)
    h = sub1(r'(<text x="65" y="61"[^>]*?)font-size="\d+"([^>]*>)[^<]*(</text>\s*<text x="65" y="78"[^>]*>)[^<]*(</text>)',
             lambda m: m.group(1) + f'font-size="{fs}"' + m.group(2) + big + m.group(3) + small + m.group(4), h)

    # rodape (texto de fonte e carimbo)
    how = ("consultado automaticamente pela API oficial do Power&nbsp;BI" if getattr(s, "source", "api") == "api"
           else "lido automaticamente do link público (Publicar na Web) do relatório")
    stamp = f" Base do relatório atualizada em {day.source_stamp}." if getattr(day, "source_stamp", "") else ""
    src = (f'<div class="src">Fonte: relatório "Materiais Aplicados - Por Equipamento - UMOE" do Power&nbsp;BI, '
           f"{how}, com o dia definido para {D}.{stamp} "
           "Os gráficos de tendência mensal (diário e acumulado) usam o total de cada dia do mês corrente, "
           "recalculado a cada atualização (valores de dias anteriores podem ser revisados pelo Power&nbsp;BI).</div>")
    h = sub1(r'<div class="src">.*?</div>', lambda m: src, h)
    h = sub1(r"<div>Gerado por Claude · [^<]*</div>",
             lambda m: f"<div>Atualizado automaticamente · {now_s} (America/Sao_Paulo)</div>", h)

    # historico do mes (JSON embutido; o script de renderizacao dos graficos nao muda)
    md = {"month": f"{day.date.year:04d}-{day.date.month:02d}", "updatedAt": now_s, "daily": month_daily}
    block = '<script id="month-data" type="application/json">\n' + json.dumps(md, indent=2) + "\n</script>"
    h = sub1(r'<script id="month-data" type="application/json">.*?</script>', lambda m: block, h)
    first, last = sorted(month_daily)[0], sorted(month_daily)[-1]
    rng = f"{first[8:10]}/{first[5:7]} a {last[8:10]}/{last[5:7]}"
    h = re.sub(r'(<span class="month-range-label">)[^<]*(</span>)', lambda m: m.group(1) + rng + m.group(2), h)
    h = re.sub(r'(<span class="month-name-label">)[^<]*(</span>)',
               lambda m: m.group(1) + f"{MONTHS_PT[day.date.month - 1]}/{day.date.year}" + m.group(2), h)
    return h


PAGE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>Materiais Aplicados - Por Dia/Equipamentos</title>
<style>:root{{color-scheme:light dark}}html,body{{margin:0;padding:0}}body{{font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#f9f9f7;color:#0b0b0b}}
@media (prefers-color-scheme: dark){{body{{background:#0d0d0d}}}}img{{max-width:100%}}</style></head>
<body>
{body}
</body></html>
"""


def render_page(day, month_daily, now_s, s) -> str:
    return PAGE.format(body=render_fragment(day, month_daily, now_s, s))
