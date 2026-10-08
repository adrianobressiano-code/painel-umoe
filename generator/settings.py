"""Configuracao: nomes do modelo em config.json; segredos SOMENTE em variaveis de ambiente."""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    workspace_id: str = ""
    dataset_id: str = ""
    table: str = "Materiais"
    columns: dict = field(default_factory=dict)
    value_expr: str = ""
    source: str = "web"     # "web" = link publico (Publicar na Web) | "api" = API oficial (Azure)
    public_url: str = ""
    timezone: str = "America/Sao_Paulo"
    gauge_max: int = 58000
    keep_upper: list = field(default_factory=list)

    def c(self, key: str) -> str:
        return self.columns[key]


def load(path: Path | None = None) -> Settings:
    cfg = json.loads((path or ROOT / "config.json").read_text(encoding="utf8"))
    env = os.environ.get
    return Settings(
        tenant_id=env("PBI_TENANT_ID", ""), client_id=env("PBI_CLIENT_ID", ""),
        client_secret=env("PBI_CLIENT_SECRET", ""),
        workspace_id=env("PBI_WORKSPACE_ID", cfg.get("workspace_id", "")),
        dataset_id=env("PBI_DATASET_ID", cfg.get("dataset_id", "")),
        table=cfg["table"], columns=cfg["columns"], value_expr=cfg.get("value_expr", ""),
        source=env("PBI_SOURCE", cfg.get("source", "web")), public_url=env("PBI_PUBLIC_URL", ""),
        timezone=cfg.get("timezone", "America/Sao_Paulo"), gauge_max=int(cfg.get("gauge_max", 58000)),
        keep_upper=cfg.get("keep_upper", []),
    )
