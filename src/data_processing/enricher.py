from pathlib import Path

import pandas as pd


SRC_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = SRC_DIR / "data" / "raw"
PROCESSED_DATA_DIR = SRC_DIR / "data" / "processed"


def cruzar_cvm_com_macro(df_cvm_limpo):
    """Cruza os dados limpos da CVM com indicadores macro e IFIX."""
    print("Enriquecendo ofertas com dados macroeconomicos e IFIX...")

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        caminho_macro = RAW_DATA_DIR / "macro_bcb_bruto.csv"
        if caminho_macro.exists():
            df_macro = pd.read_csv(caminho_macro, sep=";")
            df_macro["data"] = pd.to_datetime(df_macro["data"])
        else:
            df_selic = pd.read_csv(RAW_DATA_DIR / "selic_bruto.csv", sep=";")
            df_selic["data"] = pd.to_datetime(df_selic["data"])
            df_macro = df_selic.rename(columns={"valor": "Taxa_Selic_Data_Oferta"})

        df_ifix = pd.read_csv(RAW_DATA_DIR / "ifix_bruto.csv", sep=";")
        df_ifix["Date"] = pd.to_datetime(df_ifix["Date"])

        if df_ifix["Date"].dt.tz is not None:
            df_ifix["Date"] = df_ifix["Date"].dt.tz_localize(None)

        df_cvm_limpo = df_cvm_limpo.sort_values("Data_requerimento")
        df_macro = df_macro.sort_values("data")
        df_ifix = df_ifix.sort_values("Date")

        df_enriquecido = pd.merge_asof(
            df_cvm_limpo,
            df_macro,
            left_on="Data_requerimento",
            right_on="data",
            direction="backward",
        )
        df_enriquecido.drop(columns=["data"], inplace=True)

        df_enriquecido = pd.merge_asof(
            df_enriquecido,
            df_ifix[["Date", "Close"]],
            left_on="Data_requerimento",
            right_on="Date",
            direction="backward",
        )
        df_enriquecido.rename(columns={"Close": "Pontos_IFIX_Data_Oferta"}, inplace=True)
        df_enriquecido.drop(columns=["Date"], inplace=True)

        colunas_arredondar = [
            "Taxa_Selic_Data_Oferta",
            "IPCA_12m_Data_Oferta",
            "CDI_Data_Oferta",
            "USD_BRL_Data_Oferta",
            "Pontos_IFIX_Data_Oferta",
        ]
        for coluna in colunas_arredondar:
            if coluna in df_enriquecido.columns:
                df_enriquecido[coluna] = df_enriquecido[coluna].round(2)

        df_enriquecido = df_enriquecido.sort_values(
            by="Data_requerimento",
            ascending=False,
        )

        caminho_final = PROCESSED_DATA_DIR / "ofertas_fiis_pronto_para_ia.csv"
        df_enriquecido.to_csv(caminho_final, sep=";", index=False, encoding="utf-8")

        print(f"Enriquecimento concluido. Arquivo final salvo em: {caminho_final}")
        return df_enriquecido

    except Exception as e:
        print(f"Erro ao cruzar dados: {e}")
        return None
