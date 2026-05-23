from pathlib import Path

import pandas as pd
import requests
import yfinance as yf


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "src" / "data" / "raw"


def obter_selic(data_inicio="01/01/2023", data_fim="31/12/2026"):
    """Obtem a taxa Selic diaria do Banco Central do Brasil (SGS)."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Obtendo dados da Selic de {data_inicio} a {data_fim}...")

    url = (
        "http://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados"
        f"?formato=json&dataInicial={data_inicio}&dataFinal={data_fim}"
    )

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        df_selic = pd.DataFrame(resp.json())
        df_selic["data"] = pd.to_datetime(df_selic["data"], format="%d/%m/%Y")
        df_selic["valor"] = pd.to_numeric(df_selic["valor"])

        caminho_saida = RAW_DATA_DIR / "selic_bruto.csv"
        df_selic.to_csv(caminho_saida, index=False, sep=";")
        print(f"Dados da Selic salvos em: {caminho_saida}")
        return df_selic
    except Exception as e:
        print(f"Erro ao obter a Selic: {e}")
        return None


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
    obter_selic()
    obter_ifix()
