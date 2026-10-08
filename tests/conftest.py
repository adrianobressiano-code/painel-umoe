import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _never_touch_real_history(monkeypatch, tmp_path):
    """Os testes nunca podem escrever em data/history.json de verdade."""
    from generator import history
    monkeypatch.setattr(history, "PATH", tmp_path / "hist_teste" / "history.json")
