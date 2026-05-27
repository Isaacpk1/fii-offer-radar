from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    import duckdb
except ImportError as exc:
    raise SystemExit(
        "DuckDB nao esta instalado. Rode `pip install -r requirements.txt` "
        "antes de gerar o warehouse."
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
RAW_DATA_DIR = SRC_DIR / "data" / "raw"
PROCESSED_DATA_DIR = SRC_DIR / "data" / "processed"
DATABASE_PATH = PROCESSED_DATA_DIR / "fii_warehouse.duckdb"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
MANAGED_TABLES = [
    "data_quality_report",
    "oferta_inteligencia",
    "oferta_documento_extracoes_llm",
    "oferta_documento_extracoes",
    "oferta_projecoes",
    "fii_metricas",
    "noticias_fiis",
    "macro_series",
    "fii_portfolio",
    "fii_rendimentos",
    "fii_cotacoes",
    "fii_informe_mensal",
    "ofertas_cvm",
    "dim_fii",
]

def _read_csv(path: Path, required: bool = False) -> pd.DataFrame:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Arquivo obrigatorio nao encontrado: {path}")
        return pd.DataFrame()
    return pd.read_csv(path, sep=";", encoding="utf-8", low_memory=False)


def _to_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column in df.columns:
            text = df[column].astype(str).str.strip()
            text = text.mask(
                text.str.contains(",", regex=False),
                text.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
            )
            df[column] = pd.to_numeric(text, errors="coerce")
    return df


def _to_datetime(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", utc=True).dt.tz_localize(None)
    return df


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA
    return df[columns].copy()


def _coalesce_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Une colunas com mesmo nome mantendo o primeiro valor nao nulo por linha."""
    if not df.columns.duplicated().any():
        return df

    result = pd.DataFrame(index=df.index)
    for column in dict.fromkeys(df.columns):
        selected = df.loc[:, df.columns == column]
        if selected.shape[1] == 1:
            result[column] = selected.iloc[:, 0]
        else:
            result[column] = selected.bfill(axis=1).iloc[:, 0]
    return result


def _normalizar_yield_mensal(series: pd.Series) -> pd.Series:
    """Mantem yields mensais plausiveis e remove outliers de origem/escala."""
    values = pd.to_numeric(series, errors="coerce")
    values = values.mask(values.abs() > 1, values / 100)
    return values.where(values.between(-0.5, 0.5))


def _register_replace(con: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame) -> None:
    con.execute(f"DELETE FROM {table}")
    if df.empty:
        return
    con.register("_df_to_load", df)
    con.execute(f"INSERT INTO {table} SELECT * FROM _df_to_load")
    con.unregister("_df_to_load")


