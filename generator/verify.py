"""Confere se o mapeamento (tabela/colunas/medida) bate com os valores JA CONHECIDOS do relatorio.

Uso: python -m generator.verify      (ou workflow 'Verificar valores')
Compara os totais diarios de outubro/2026 lidos manualmente no relatorio (tests/expected_daily.json)
com o que a API devolve. Se nao bater, o mapeamento esta errado -> NAO ligue a atualizacao automatica.
"""
import json
import sys
from datetime import date

from . import model, settings


def main() -> int:
    s = settings.load()
    exp = json.load(open(settings.ROOT / "tests" / "expected_daily.json"))
    got = model.fetch_month(s, date(2026, 10, max(int(k[-2:]) for k in exp["daily"])))
    ok = True
    for k, v in sorted(exp["daily"].items()):
        g = got.get(k)
        tol = max(2, int(v * 0.0005))
        flag = "OK " if g is not None and abs(g - v) <= tol else "DIFF"
        ok &= flag == "OK "
        print(f"{flag} {k}  esperado={v:>9}  api={g}")
    print("\nRESULTADO:", "tudo bate - pode ativar" if ok else "NAO BATE - revise config.json (tabela/colunas/medida)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
