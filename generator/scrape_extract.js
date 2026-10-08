async (opts) => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const kindOf = (head) => {
    if (head.includes("Descrição Material")) return "detail";
    if (head.includes("Classe Manutenção")) return "classes";
    if (head.includes("Centro Custo")) return "cost_centers";
    if (head.includes("Tipo Peças/Serviços")) return "parts";
    if (head.includes("Frota") && head.includes("Modelo")) return "fleet";
    return null;
  };
  const rowsOf = (m) =>
    (m.innerText || "")
      .split("Selecionar Linha")
      .map((chunk) => chunk.split("\n").map((s) => s.replace(/\u00a0/g, " ").trim()).filter((s) => s !== ""))
      .filter((t) => t.length > 0);
  const out = {};
  for (const m of document.querySelectorAll(".mid-viewport")) {
    const v = m.closest(".visualContainer");
    if (!v) continue;
    const head = (v.innerText || "").split("Selecionar Linha")[0];
    const kind = kindOf(head);
    if (!kind) continue;
    const seen = new Set();
    const rows = [];
    const snap = () => {
      let added = 0;
      for (const t of rowsOf(m)) {
        const key = JSON.stringify(t);
        if (!seen.has(key)) { seen.add(key); rows.push(t); added++; }
      }
      return added;
    };
    m.scrollTop = 0;
    await sleep(500);
    snap();
    const maxSteps = kind === "detail" ? 0 : 120;   // detalhamento: so as primeiras linhas (ordenado por valor)
    for (let i = 0; i < maxSteps; i++) {
      if (m.scrollTop + m.clientHeight >= m.scrollHeight - 2) {
        // chegou ao fim do que esta renderizado: espera o Power BI carregar mais linhas (se houver)
        const before = m.scrollHeight;
        m.scrollTop = m.scrollHeight;
        await sleep(1500);
        snap();
        if (m.scrollHeight <= before + 2) break;
        continue;
      }
      m.scrollTop = m.scrollTop + Math.max(40, Math.floor(m.clientHeight * 0.7));
      await sleep(450);
      snap();
    }
    m.scrollTop = 0;
    out[kind] = { rows, scrollHeight: m.scrollHeight, clientHeight: m.clientHeight };
  }
  const txt = document.body.innerText;
  out.hero = (txt.match(/\n([\d.\-]+|\(Em branc[^\n]*)\nValor Total/) || [])[1] || null;
  out.stamp = (txt.match(/Valor Total\n(\d\d\/\d\d\/\d\d \d\d:\d\d)\n/) || [])[1] || null;
  const inp = (k) => [...document.querySelectorAll('input[type="text"]')].find((i) => (i.getAttribute("aria-label") || "").startsWith(k));
  out.start = inp("Data de início") ? inp("Data de início").value : null;
  out.end = inp("Data de término") ? inp("Data de término").value : null;
  return out;
}
