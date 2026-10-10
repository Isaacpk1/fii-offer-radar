from __future__ import annotations

import json

import pandas as pd

from database.build_common import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    _ensure_columns,
    _read_csv,
    _to_datetime,
    _to_numeric,
)


def _build_cotacoes() -> pd.DataFrame:
    mercado = _read_csv(RAW_DATA_DIR / "fii_mercado_bruto.csv")
    if mercado.empty:
        return pd.DataFrame()

    mercado = _ensure_columns(
        mercado,
        ["Ticker", "Preco_Cota", "Volume_Medio_Diario", "Volume_Cotas_Medio_Diario"],
    )
    mercado = _to_numeric(mercado, ["Preco_Cota", "Volume_Medio_Diario", "Volume_Cotas_Medio_Diario"])
    mercado["data"] = pd.Timestamp.today().normalize()
    mercado["volume_financeiro"] = mercado["Volume_Medio_Diario"]
    mercado["fonte"] = "Yahoo Finance via yfinance"
    mercado = mercado.rename(
        columns={
            "Ticker": "ticker",
            "Preco_Cota": "preco_fechamento",
            "Volume_Medio_Diario": "volume_medio_diario",
        }
    )
    return mercado[
        ["ticker", "data", "preco_fechamento", "volume_financeiro", "volume_medio_diario", "fonte"]
    ].dropna(subset=["ticker"]).drop_duplicates(["ticker", "data"], keep="last")


def _build_macro() -> pd.DataFrame:
    macro = _read_csv(RAW_DATA_DIR / "macro_bcb_bruto.csv")
    if macro.empty:
        return pd.DataFrame()

    ifix = _read_csv(RAW_DATA_DIR / "ifix_bruto.csv")
    macro = macro.rename(
        columns={
            "data": "data",
            "Taxa_Selic_Data_Oferta": "taxa_selic",
            "IPCA_12m_Data_Oferta": "ipca_12m",
            "CDI_Data_Oferta": "cdi",
            "USD_BRL_Data_Oferta": "usd_brl",
        }
    )
    macro = _ensure_columns(macro, ["data", "taxa_selic", "ipca_12m", "cdi", "usd_brl"])
    macro = _to_datetime(macro, ["data"])
    macro = _to_numeric(macro, ["taxa_selic", "ipca_12m", "cdi", "usd_brl"])
    macro = macro.sort_values("data")
    macro[["taxa_selic", "ipca_12m", "cdi", "usd_brl"]] = macro[
        ["taxa_selic", "ipca_12m", "cdi", "usd_brl"]
    ].ffill()

    if not ifix.empty:
        ifix = ifix.rename(columns={"Date": "data", "Close": "ifix"})
        ifix = _ensure_columns(ifix, ["data", "ifix"])
        ifix = _to_datetime(ifix, ["data"])
        ifix = _to_numeric(ifix, ["ifix"])
        macro = pd.merge_asof(
            macro,
            ifix.dropna(subset=["data"]).sort_values("data"),
            on="data",
            direction="backward",
        )
    else:
        macro["ifix"] = pd.NA

    return macro.dropna(subset=["data"]).drop_duplicates("data", keep="last")


def _build_noticias() -> pd.DataFrame:
    path = PROCESSED_DATA_DIR / "noticias_fiis.json"
    if not path.exists():
        return pd.DataFrame()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return pd.DataFrame()

    noticias = payload.get("noticias", []) if isinstance(payload, dict) else []
    if not noticias:
        return pd.DataFrame()

    coletado_em = payload.get("atualizado_em") if isinstance(payload, dict) else None
    df = pd.DataFrame(noticias)
    df = _ensure_columns(df, ["fonte", "titulo", "data", "resumo", "url"])
    for column in ["fonte", "titulo", "data", "resumo", "url"]:
        df[column] = df[column].astype(str).str.strip()

    df = df[(df["titulo"] != "") & (df["url"] != "")]
    if df.empty:
        return pd.DataFrame()

    df["texto_busca"] = (
        df["fonte"].fillna("")
        + " "
        + df["titulo"].fillna("")
        + " "
        + df["resumo"].fillna("")
        + " "
        + df["url"].fillna("")
    ).str.lower()
    df["coletado_em"] = pd.to_datetime(coletado_em, errors="coerce")
    df = df.rename(columns={"data": "data_publicacao"})
    return df[
        ["fonte", "titulo", "data_publicacao", "resumo", "url", "texto_busca", "coletado_em"]
    ].drop_duplicates(["fonte", "titulo", "url"], keep="last")


