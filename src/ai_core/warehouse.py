from __future__ import annotations

import duckdb
import pandas as pd

from ai_core.tool_config import CSV_PATH, WAREHOUSE_PATH


def _warehouse_disponivel() -> bool:
    return WAREHOUSE_PATH.exists()


def _query_warehouse(sql: str, params: list | None = None) -> pd.DataFrame:
    if not _warehouse_disponivel():
        raise FileNotFoundError(
            "Warehouse DuckDB nao encontrado. Rode `python src/database/build_database.py`."
        )
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
        return con.execute(sql, params or []).df()


def _table_columns(table: str) -> set[str]:
    if not _warehouse_disponivel():
        return set()
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
        return set(con.execute(f"DESCRIBE {table}").df()["column_name"].astype(str))


def _select_existing_columns(table: str, columns: list[str]) -> list[str]:
    existing = _table_columns(table)
    return [column for column in columns if column in existing]


def _carregar_base_csv() -> pd.DataFrame:
    return pd.read_csv(CSV_PATH, sep=";", encoding="utf-8")


def _normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in normalized.columns:
        if pd.api.types.is_datetime64_any_dtype(normalized[column]):
            normalized[column] = normalized[column].dt.strftime("%Y-%m-%d")
    return normalized.astype(object).where(pd.notna(normalized), None)


def _to_json(df: pd.DataFrame) -> str:
    if df.empty:
        return "[]"
    return _normalizar_df(df).to_json(orient="records", force_ascii=False)


def _limite(valor: str, default: int = 10, maximum: int = 30) -> int:
    try:
        parsed = int(str(valor).strip())
    except Exception:
        parsed = default
    return max(1, min(parsed, maximum))


def _tokens_busca(texto: str) -> list[str]:
    tokens = []
    for raw in str(texto).replace("/", " ").replace("-", " ").split():
        token = "".join(char for char in raw.lower() if char.isalnum())
        if len(token) >= 3 and token not in tokens:
            tokens.append(token)
    return tokens[:8]
