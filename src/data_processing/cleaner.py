from pathlib import Path

import pandas as pd

try:
    from data_processing.utils import para_numero
except ModuleNotFoundError:
    from utils import para_numero


SRC_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = SRC_DIR / "data" / "raw"

COLUNAS_OFERTA_FII = [
    "Numero_Requerimento",
    "Rito_Requerimento",
    "Numero_Processo",
    "Data_requerimento",
    "Data_Registro",
    "Data_Encerramento",
    "Status_Requerimento",
    "Valor_Mobiliario",
    "Tipo_requerimento",
    "Bookbuilding",
    "CNPJ_Emissor",
    "Nome_Emissor",
    "CNPJ_Lider",
    "Nome_Lider",
    "Grupo_Coordenador",
    "Tipo_Oferta",
    "Emissao",
    "Qtde_Total_Registrada",
    "Valor_Total_Registrado",
    "Oferta_inicial",
    "Oferta_vasos_comunicantes",
    "Publico_alvo",
    "Destinacao_recursos",
    "Data_deliberacao_aprovou_oferta",
    "Mercado_negociacao",
    "Regime_distribuicao",
    "Administrador",
    "Gestor",
    "Escriturador",
    "Custodiante",
    "Num_Invest_Pessoa_Natural",
    "Qtde_VM_Pessoa_Natural",
    "Num_Invest_Fundos_Investimento",
    "Qtde_VM_Fundos_Investimento",
    "Num_Invest_Investidor_Estrangeiro",
    "Qtde_VM_Investidor_Estrangeiro",
    "Num_Invest_Demais_Pessoa_Juridica",
    "Qtde_VM_Demais_Pessoa_Juridica",
]

COLUNAS_DATA = [
    "Data_requerimento",
    "Data_Registro",
    "Data_Encerramento",
    "Data_deliberacao_aprovou_oferta",
]

COLUNAS_NUMERICAS = [
    "Numero_Requerimento",
    "Emissao",
    "Qtde_Total_Registrada",
    "Valor_Total_Registrado",
    "Num_Invest_Pessoa_Natural",
    "Qtde_VM_Pessoa_Natural",
    "Num_Invest_Fundos_Investimento",
    "Qtde_VM_Fundos_Investimento",
    "Num_Invest_Investidor_Estrangeiro",
    "Qtde_VM_Investidor_Estrangeiro",
    "Num_Invest_Demais_Pessoa_Juridica",
    "Qtde_VM_Demais_Pessoa_Juridica",
]


def limpar_dados_cvm():
    """Le os dados brutos da CVM, filtra FIIs e formata as colunas."""
    caminho_bruto = RAW_DATA_DIR / "oferta_resolucao_160_bruto.csv"
    print(f"Limpando dados da CVM a partir de: {caminho_bruto}")

    try:
        df = pd.read_csv(caminho_bruto, sep=";", encoding="utf-8", low_memory=False)
        df_fiis = df[df["Valor_Mobiliario"] == "Cotas de FII"].copy()

        colunas_existentes = [col for col in COLUNAS_OFERTA_FII if col in df_fiis.columns]
        df_limpo = df_fiis[colunas_existentes].copy()

        for coluna in COLUNAS_DATA:
            if coluna in df_limpo.columns:
                df_limpo[coluna] = pd.to_datetime(df_limpo[coluna], errors="coerce")

        for coluna in COLUNAS_NUMERICAS:
            if coluna in df_limpo.columns:
                df_limpo[coluna] = para_numero(df_limpo[coluna])

        if "Data_requerimento" in df_limpo.columns:
            df_limpo = df_limpo.dropna(subset=["Data_requerimento"])
            df_limpo = df_limpo.sort_values(by="Data_requerimento", ascending=False)

        print(f"Limpeza concluida: {len(df_limpo)} ofertas de FIIs prontas para cruzamento.")
        return df_limpo

    except Exception as e:
        print(f"Erro ao limpar dados da CVM: {e}")
        return None
