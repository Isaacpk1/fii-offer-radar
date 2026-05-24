from pathlib import Path

from bcb import sgs
import pandas as pd
import yfinance as yf


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "src" / "data" / "raw"
MACRO_SERIES = {
    "Taxa_Selic_Data_Oferta": 11,
    "IPCA_12m_Data_Oferta": 13522,
    "CDI_Data_Oferta": 12,
    "USD_BRL_Data_Oferta": 1,
}


def obter_indicadores_macro(data_inicio="2023-01-01", data_fim="2026-12-31"):
    """Obtem Selic, IPCA 12m, CDI e USD/BRL pelo SGS do Banco Central."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Obtendo indicadores macro de {data_inicio} a {data_fim}...")

    try:
        df_macro = sgs.get(MACRO_SERIES, start=data_inicio, end=data_fim)
        df_macro = df_macro.reset_index().rename(columns={"Date": "data"})
        df_macro["data"] = pd.to_datetime(df_macro["data"])

        caminho_saida = RAW_DATA_DIR / "macro_bcb_bruto.csv"
        df_macro.to_csv(caminho_saida, index=False, sep=";")

        # Mantem compatibilidade com versoes anteriores do pipeline.
        df_macro[["data", "Taxa_Selic_Data_Oferta"]].rename(
            columns={"Taxa_Selic_Data_Oferta": "valor"}
        ).to_csv(RAW_DATA_DIR / "selic_bruto.csv", index=False, sep=";")

        print(f"Indicadores macro salvos em: {caminho_saida}")
        return df_macro
    except Exception as e:
        print(f"Erro ao obter indicadores macro: {e}")
        return None


def obter_selic(data_inicio="01/01/2023", data_fim="31/12/2026"):
    """Compatibilidade: obtem somente a serie Selic a partir do CSV macro."""
    inicio_iso = pd.to_datetime(data_inicio, dayfirst=True).strftime("%Y-%m-%d")
    fim_iso = pd.to_datetime(data_fim, dayfirst=True).strftime("%Y-%m-%d")
    df_macro = obter_indicadores_macro(inicio_iso, fim_iso)
    if df_macro is None:
        return None
    return df_macro[["data", "Taxa_Selic_Data_Oferta"]].rename(
        columns={"Taxa_Selic_Data_Oferta": "valor"}
    )


def obter_ifix(data_inicio="2023-01-01", data_fim="2026-12-31"):
    """Obtem o historico do IFIX (Indice de Fundos Imobiliarios) via yfinance."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Obtendo dados do IFIX de {data_inicio} a {data_fim}...")

    try:
        ticker = yf.Ticker("IFIX.SA")
        ifix = ticker.history(start=data_inicio, end=data_fim)
        ifix.reset_index(inplace=True)

        if "Date" not in ifix.columns and "Datetime" in ifix.columns:
            ifix.rename(columns={"Datetime": "Date"}, inplace=True)

        ifix_clean = ifix[["Date", "Close"]].copy()

        caminho_saida = RAW_DATA_DIR / "ifix_bruto.csv"
        ifix_clean.to_csv(caminho_saida, index=False, sep=";")
        print(f"Dados do IFIX salvos em: {caminho_saida}")
        return ifix_clean
    except Exception as e:
        print(f"Erro ao obter o IFIX: {e}")
        return None


if __name__ == "__main__":
    obter_indicadores_macro()
    obter_ifix()
