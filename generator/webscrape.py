"""Le o relatorio pelo link publico ("Publicar na Web") com um navegador headless (Playwright).

Nao precisa de login, Azure nem administrador. Troca o filtro "Data Aplicação." e le as tabelas.
O link e tratado como SEGREDO (quem tem o link ve os dados): vem da variavel PBI_PUBLIC_URL.
"""
import time
from datetime import date
from pathlib import Path

from .parse import ParseError, check_detail_sorted, num, parse_day

EXTRACT_JS = (Path(__file__).with_name("scrape_extract.js")).read_text(encoding="utf8").strip()

SET_JS = """
async ([key, value]) => {
  const el = [...document.querySelectorAll('input[type="text"]')].find(i => (i.getAttribute('aria-label')||'').startsWith(key));
  if (!el) return false;
  el.focus();
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, value);
  el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true}));
  el.blur();
  return true;
}
"""

STATE_JS = """
() => {
  const q = k => { const e = [...document.querySelectorAll('input[type="text"]')].find(i => (i.getAttribute('aria-label')||'').startsWith(k)); return e ? e.value : null; };
  const t = document.body.innerText;
  return { start: q('Data de início'), end: q('Data de término'),
           hero: (t.match(/\\n([\\d.\\-]+|\\(Em branc[^\\n]*)\\nValor Total/) || [])[1] || null,
           sig: t.length + ':' + document.querySelectorAll('.mid-viewport').length };
}
"""


def fmt(d: date) -> str:
    return d.strftime("%d/%m/%Y")


class Scraper:
    def __init__(self, url: str, headless: bool = True, log=print):
        if not url:
            raise ParseError("PBI_PUBLIC_URL nao configurado (GitHub > Settings > Secrets)")
        self.url, self.headless, self.log = url, headless, log

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page(viewport={"width": 1400, "height": 900}, locale="pt-BR",
                                          timezone_id="America/Sao_Paulo")
        self.page.goto(self.url, wait_until="domcontentloaded", timeout=90000)
        self.page.wait_for_function(
            "() => document.body.innerText.includes('Valor Total') && "
            "[...document.querySelectorAll('input[type=\"text\"]')].some(i => (i.getAttribute('aria-label')||'').startsWith('Data de início'))",
            timeout=120000)
        self.settle()
        return self

    def __exit__(self, *exc):
        try:
            self.browser.close()
        finally:
            self._pw.stop()

    def screenshot(self, path: str):
        self.page.screenshot(path=path, full_page=True)

    # ------------------------------------------------------------------ espera
    def state(self) -> dict:
        return self.page.evaluate(STATE_JS)

    def settle(self, min_s: float = 4.0, timeout_s: float = 45.0, stable_reads: int = 3):
        """Espera os visuais terminarem de recarregar (assinatura da pagina estavel por varias leituras)."""
        t0, last, same = time.time(), None, 0
        while time.time() - t0 < timeout_s:
            time.sleep(0.8)
            st = self.state()
            sig = (st["hero"], st["sig"], st["start"], st["end"])
            same = same + 1 if sig == last else 0
            last = sig
            if same >= stable_reads and time.time() - t0 >= min_s:
                return st
        raise ParseError("a pagina nao estabilizou depois de trocar a data (timeout)")

    # ------------------------------------------------------------------ filtro
    def set_range(self, a: date, b: date, tries: int = 3):
        want_a, want_b = fmt(a), fmt(b)
        for attempt in range(tries):
            st = self.state()
            cur_end = st["end"]
            forward = cur_end is not None and a > _parse(cur_end)
            order = [("Data de término", want_b), ("Data de início", want_a)] if forward else \
                    [("Data de início", want_a), ("Data de término", want_b)]
            for key, val in order:
                if not self.page.evaluate(SET_JS, [key, val]):
                    raise ParseError(f"campo '{key}' nao encontrado")
                time.sleep(1.2)
            st = self.settle()
            if st["start"] == want_a and st["end"] == want_b:
                return st
            self.log(f"  filtro nao pegou (tentativa {attempt + 1}): {st['start']}..{st['end']}")
        raise ParseError(f"nao consegui fixar o filtro {want_a}..{want_b}")

    # ------------------------------------------------------------------ leitura
    def total(self, a: date, b: date | None = None) -> int:
        st = self.set_range(a, b or a)
        return num(st["hero"])

    def day(self, d: date, validator=None, attempts: int = 3):
        """Fixa o dia e le todas as tabelas. Se a leitura sair inconsistente (visuais ainda recarregando), tenta de novo."""
        self.set_range(d, d)
        last_err = None
        for n in range(attempts):
            if n:
                self.log(f"  leitura inconsistente ({last_err}); tentando de novo ({n + 1}/{attempts})")
                time.sleep(6)
            try:
                raw = self.page.evaluate(EXTRACT_JS, {})
                again = self.state()
                if again["hero"] != raw.get("hero"):
                    raise ParseError("o total mudou durante a leitura (pagina ainda carregando)")
                check_detail_sorted(raw)
                day = parse_day(raw, d)
                errs = validator(day) if validator else []
                if errs:
                    raise ParseError("; ".join(errs))
                return day
            except ParseError as e:
                last_err = str(e)
        raise ParseError(last_err)


def _parse(s: str) -> date:
    dd, mm, yy = s.split("/")
    return date(int(yy), int(mm), int(dd))


def probe(url: str, out_dir: str = "probe") -> int:
    """Diagnostico: abre o link, le o dia de hoje e salva captura de tela + dados crus (para depurar no GitHub)."""
    import json
    from datetime import datetime
    from zoneinfo import ZoneInfo

    Path(out_dir).mkdir(exist_ok=True)
    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    with Scraper(url) as sc:
        sc.set_range(today, today)
        raw = sc.page.evaluate(EXTRACT_JS, {})
        sc.screenshot(f"{out_dir}/pagina.png")
        Path(f"{out_dir}/cru.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf8")
        day = parse_day(raw, today)
    print(f"data={today} total=R$ {day.total} classes={len(day.classes)} centros={len(day.cost_centers)} "
          f"frota={len(day.fleet)} peças={len(day.parts)} materiais={len(day.materials)} base={day.source_stamp}")
    return 0
