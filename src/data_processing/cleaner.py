from pathlib import Path

import pandas as pd


SRC_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = SRC_DIR / "data" / "raw"


def limpar_dados_cvm():
    """Le os dados brutos da CVM, filtra FIIs e formata as colunas."""
    caminho_bruto = RAW_DATA_DIR / "oferta_resolucao_160_bruto.csv"
    print(f"Limpando dados da CVM a partir de: {caminho_bruto}")

    try:
        df = pd.read_csv(caminho_bruto, sep=";", encoding="utf-8", low_memory=False)
        df_fiis = df[df["Valor_Mobiliario"] == "Cotas de FII"].copy()

        colunas_interesse = [
            "Numero_Processo",
            "Data_requerimento",
            "Nome_Emissor",
            "CNPJ_Emissor",
            "Nome_Lider",
            "Tipo_Oferta",
            "Valor_Total_Registrado",
            "Status_Requerimento",
            "Publico_alvo",
        ]

        colunas_existentes = [col for col in colunas_interesse if col in df_fiis.columns]
        df_limpo = df_fiis[colunas_existentes].copy()

        if "Data_requerimento" in df_limpo.columns:
            df_limpo["Data_requerimento"] = pd.to_datetime(
                df_limpo["Data_requerimento"],
                errors="coerce",
            )
            df_limpo = df_limpo.dropna(subset=["Data_requerimento"])
            df_limpo = df_limpo.sort_values(by="Data_requerimento", ascending=False)

        print(f"Limpeza concluida: {len(df_limpo)} ofertas de FIIs prontas para cruzamento.")
        return df_limpo

    except Exception as e:
        print(f"Erro ao limpar dados da CVM: {e}")
        return None
