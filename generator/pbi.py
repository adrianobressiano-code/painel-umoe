"""Cliente da API oficial do Power BI (executeQueries) com identidade de aplicativo (sem login humano)."""
import json
import re
import time
from datetime import date
from typing import Any

import httpx

API = "https://api.powerbi.com/v1.0/myorg"
SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]


class PowerBIError(RuntimeError):
    pass


def get_token(s) -> str:
    import msal

    for k in ("tenant_id", "client_id", "client_secret"):
        if not getattr(s, k):
            raise PowerBIError(f"Segredo ausente: {k} (configure em GitHub > Settings > Secrets)")
    app = msal.ConfidentialClientApplication(
        s.client_id, authority=f"https://login.microsoftonline.com/{s.tenant_id}",
        client_credential=s.client_secret)
    res = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in res:
        raise PowerBIError("Falha de autenticacao: " + str(res.get("error_description", res))[:400])
    return res["access_token"]


_token_cache: dict[str, str] = {}


def execute_queries(dax: str, s, retries: int = 3) -> list[dict[str, Any]]:
    """Executa DAX e devolve as linhas. Tenta de novo em erros temporarios (429/5xx/rede)."""
    url = f"{API}/groups/{s.workspace_id}/datasets/{s.dataset_id}/executeQueries"
    body = {"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}}
    last = ""
    for attempt in range(retries):
        try:
            tok = _token_cache.get("t") or _token_cache.setdefault("t", get_token(s))
            r = httpx.post(url, headers={"Authorization": "Bearer " + tok}, json=body, timeout=90)
            if r.status_code == 401:
                _token_cache.clear()
            if r.status_code in (401, 429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}"
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code >= 400:
                raise PowerBIError(f"executeQueries {r.status_code}: {r.text[:500]}")
            data = r.json()
            res = data["results"][0]
            if res.get("error"):
                raise PowerBIError("Erro DAX: " + json.dumps(res["error"])[:500])
            return res["tables"][0].get("rows", [])
        except (httpx.TransportError, KeyError, IndexError) as e:
            last = repr(e)
            time.sleep(5 * (attempt + 1))
    raise PowerBIError(f"Power BI indisponivel apos {retries} tentativas ({last})")


def col(row: dict, name: str) -> Any:
    for k, v in row.items():
        m = re.search(r"\[(.*)\]$", k)
        if (m.group(1) if m else k) == name:
            return v
    return None


# ------------------------------------------------------------------ DAX
def q(name: str) -> str:
    return "'" + name.replace("'", "''") + "'"


def ident(s, key: str) -> str:
    return f"{q(s.table)}[{s.c(key)}]"


def dax_date(d: date) -> str:
    return f"DATE({d.year},{d.month},{d.day})"


def value_expr(s) -> str:
    return s.value_expr or f"SUM({ident(s, 'value')})"


def _day_filter(s, d: date) -> str:
    dc = ident(s, "date")
    return f"FILTER(ALL({dc}), INT({dc}) = INT({dax_date(d)}))"


def dax_total_day(s, d: date) -> str:
    return f'EVALUATE ROW("Total", CALCULATE({value_expr(s)}, {_day_filter(s, d)}))'


def dax_group(s, d: date, keys: list[str]) -> str:
    cols = ", ".join(ident(s, k) for k in keys)
    return (f'EVALUATE SUMMARIZECOLUMNS({cols}, {_day_filter(s, d)}, "Total", {value_expr(s)}) '
            f"ORDER BY [Total] DESC")


def dax_materials(s, d: date, top: int = 10) -> str:
    keys = ["os", "material_code", "material_desc", "fleet", "model"]
    cols = ", ".join(ident(s, k) for k in keys)
    inner = (f'SUMMARIZECOLUMNS({cols}, {_day_filter(s, d)}, '
             f'"Qtd", SUM({ident(s, "qty")}), "Total", {value_expr(s)})')
    return f"EVALUATE TOPN({top}, {inner}, [Total], DESC) ORDER BY [Total] DESC"


def dax_daily(s, year: int, month: int) -> str:
    dc = ident(s, "date")
    return (f"EVALUATE SUMMARIZECOLUMNS({dc}, "
            f"FILTER(ALL({dc}), YEAR({dc}) = {year} && MONTH({dc}) = {month}), "
            f'"Total", {value_expr(s)}) ORDER BY {dc} ASC')


def dax_discover() -> str:
    return "EVALUATE COLUMNSTATISTICS()"
