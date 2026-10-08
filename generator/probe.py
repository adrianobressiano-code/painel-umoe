"""Diagnostico do link publico.  Uso: PBI_PUBLIC_URL=... python -m generator.probe"""
import os
import sys

from .webscrape import probe

if __name__ == "__main__":
    sys.exit(probe(os.environ.get("PBI_PUBLIC_URL", "")))
