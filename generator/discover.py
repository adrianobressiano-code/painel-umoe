"""Lista tabelas/colunas do modelo para preencher config.json.  Uso: python -m generator.discover"""
import sys

from . import pbi, settings


def main() -> int:
    s = settings.load()
    rows = pbi.execute_queries(pbi.dax_discover(), s)
    print("TABELA | COLUNA")
    for r in sorted(rows, key=lambda r: (str(r.get("[Table Name]")), str(r.get("[Column Name]")))):
        print(f"{r.get('[Table Name]')} | {r.get('[Column Name]')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
