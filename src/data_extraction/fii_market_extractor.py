from pathlib import Path

import pandas as pd
import yfinance as yf

from data_extraction.fii_ticker_mapper import get_ticker_by_cnpj

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "src" / "data" / "raw"


def buscar_mercado_por_cnpj(df_cvm: pd.DataFrame) -> pd.DataFrame | None:
    """Busca preco e volume no yfinance com base nos emissores da CVM."""
    if df_cvm is None or df_cvm.empty:
        print("Aviso: base CVM vazia. Dados de mercado nao serao buscados.")
        return None

    print("Buscando dados de mercado no Yahoo Finance para precificacao e liquidez...")
    emissores = df_cvm[["CNPJ_Emissor"]].drop_duplicates().dropna()
    resultados = []

    for _, row in emissores.iterrows():
        ticker = get_ticker_by_cnpj(row["CNPJ_Emissor"])
        if not ticker:
            continue

        ticker_yahoo = f"{ticker}.SA"
        try:
            hist = yf.Ticker(ticker_yahoo).history(period="1mo")
        except Exception:
            continue

        if hist.empty:
            continue

        hist = hist.dropna(subset=["Close", "Volume"]).copy()
        if hist.empty:
            continue

        volume_financeiro = hist["Close"] * hist["Volume"]

        resultados.append(
            {
                "CNPJ_Emissor": row["CNPJ_Emissor"],
                "Ticker": ticker,
                "Preco_Cota": round(hist["Close"].iloc[-1], 2),
                "Volume_Medio_Diario": round(volume_financeiro.mean(), 2),
                "Volume_Cotas_Medio_Diario": round(hist["Volume"].mean(), 2),
            }
        )

    if not resultados:
        print("Aviso: Nenhum dado de mercado foi retornado.")
        return None

    df_mercado = pd.DataFrame(resultados).drop_duplicates(subset="CNPJ_Emissor", keep="last")
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    caminho_mercado = RAW_DATA_DIR / "fii_mercado_bruto.csv"
    df_mercado.to_csv(caminho_mercado, sep=";", index=False, encoding="utf-8")
    print(f"Dados de mercado salvos para {len(df_mercado)} FIIs mapeados.")
    return df_mercado
