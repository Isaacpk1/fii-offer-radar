from __future__ import annotations

from datetime import date, timedelta

import duckdb
from bcb import sgs

from ai_core.tool_config import MACRO_CODES, WAREHOUSE_PATH


WAREHOUSE_MACRO_COLUMNS = {
    "selic": "taxa_selic",
    "ipca": "ipca_12m",
    "ipca_12m": "ipca_12m",
    "cdi": "cdi",
    "usd_brl": "usd_brl",
    "dolar": "usd_brl",
}


def obter_macro_atual(indicador: str) -> float:
    chave = indicador.strip().lower()
    if chave not in MACRO_CODES:
        raise ValueError(f"Indicador nao suportado: {indicador}")

    try:
        return _obter_macro_bcb(chave)
    except Exception:
        return _obter_macro_warehouse(chave)


def _obter_macro_bcb(chave: str) -> float:
    # O SGS limita consultas diarias a janelas de ate 10 anos. Para valor atual,
    # uma janela curta evita erro e ainda cobre feriados/fins de semana.
    fim = date.today()
    inicio = fim - timedelta(days=45)
    serie = sgs.get({chave: MACRO_CODES[chave]}, start=inicio, end=fim)
    serie = serie.dropna()
    if serie.empty:
        raise ValueError(f"Serie macro sem dados recentes para: {chave}")
    return float(serie.iloc[-1, 0])


def _obter_macro_warehouse(chave: str) -> float:
    if not WAREHOUSE_PATH.exists():
        raise FileNotFoundError("Warehouse DuckDB nao encontrado para fallback macro.")

    coluna = WAREHOUSE_MACRO_COLUMNS.get(chave)
    if not coluna:
        raise ValueError(f"Indicador sem fallback no warehouse: {chave}")

    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
        resultado = con.execute(
            f"""
            SELECT {coluna}
            FROM macro_series
            WHERE {coluna} IS NOT NULL
            ORDER BY data DESC
            LIMIT 1
            """
        ).fetchone()

    if not resultado:
        raise ValueError(f"Indicador macro sem dado local: {chave}")
    return float(resultado[0])
