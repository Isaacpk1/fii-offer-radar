from pathlib import Path

import pandas as pd
import streamlit as st

from frontend.config import ANALISE_FII_PATH, OFERTAS_PATH, WAREHOUSE_PATH

try:
    import duckdb
except ImportError:
    duckdb = None


@st.cache_resource(show_spinner=False)
def get_connection():
    if duckdb is None or not WAREHOUSE_PATH.exists():
        return None
    return duckdb.connect(str(WAREHOUSE_PATH), read_only=True)


@st.cache_data(show_spinner=False)
def load_table(table: str) -> pd.DataFrame:
    con = get_connection()
    if con is None:
        return pd.DataFrame()
    return con.execute(f"SELECT * FROM {table}").df()


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, sep=";", encoding="utf-8", low_memory=False)


def load_ofertas() -> pd.DataFrame:
    df = load_table("ofertas_cvm")
    if df.empty:
        df = load_csv(OFERTAS_PATH)
        rename = {
            "Numero_Processo": "numero_processo",
            "CNPJ_Emissor": "cnpj_emissor",
            "Nome_Emissor": "nome_emissor",
            "Nome_Lider": "nome_lider",
            "Data_requerimento": "data_requerimento",
            "Status_Requerimento": "status_requerimento",
            "Tipo_Oferta": "tipo_oferta",
            "Publico_alvo": "publico_alvo",
            "Valor_Total_Registrado": "valor_total_registrado",
            "Taxa_Selic_Data_Oferta": "taxa_selic_data_oferta",
            "IPCA_12m_Data_Oferta": "ipca_12m_data_oferta",
            "CDI_Data_Oferta": "cdi_data_oferta",
            "USD_BRL_Data_Oferta": "usd_brl_data_oferta",
            "Pontos_IFIX_Data_Oferta": "pontos_ifix_data_oferta",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    if df.empty:
        return df

    for col in ["data_requerimento", "data_mudanca_status"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in [
        "valor_total_registrado",
        "preco_emissao",
        "taxa_selic_data_oferta",
        "ipca_12m_data_oferta",
        "cdi_data_oferta",
        "usd_brl_data_oferta",
        "pontos_ifix_data_oferta",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["nome_emissor", "nome_lider", "status_requerimento", "tipo_oferta", "publico_alvo"]:
        if col in df.columns:
            df[col] = df[col].fillna("Nao informado").astype(str)

    df = df.dropna(subset=["data_requerimento"]).copy()
    df["ano_mes"] = df["data_requerimento"].dt.to_period("M").astype(str)
    df["ano"] = df["data_requerimento"].dt.year
    return df.sort_values("data_requerimento", ascending=False)


def load_metricas() -> pd.DataFrame:
    df = load_table("fii_metricas")
    if df.empty:
        df = load_csv(ANALISE_FII_PATH)
        rename = {
            "CNPJ_Fundo": "cnpj",
            "Ticker": "ticker",
            "Patrimonio_Liquido": "patrimonio_liquido",
            "Valor_Cota_VPC": "valor_cota_vpc",
            "Preco_Cota": "preco_cota",
            "P_VP": "p_vp",
            "Preco_Emissao": "preco_emissao",
            "Volume_Medio_Diario": "volume_medio_diario",
            "Total_Emissoes": "total_emissoes",
            "Volume_Total_Ofertas": "volume_total_ofertas",
            "Coordenador_Principal": "coordenador_principal",
            "Numero_Cotistas": "numero_cotistas",
            "Status_Viabilidade_Oferta": "status_viabilidade_oferta",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    for col in [
        "patrimonio_liquido",
        "valor_cota_vpc",
        "preco_cota",
        "p_vp",
        "p_vp_emissao",
        "preco_emissao",
        "desconto_oferta_vp",
        "desconto_oferta_b3",
        "volume_medio_diario",
        "total_emissoes",
        "volume_total_ofertas",
        "numero_cotistas",
        "taxa_administracao",
        "taxa_gestao",
        "vacancia_fisica",
        "vacancia_financeira",
        "numero_imoveis",
        "dividend_yield_12m",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_oferta_inteligencia() -> pd.DataFrame:
    df = load_table("oferta_inteligencia")
    if df.empty:
        return df

    for col in ["data_requerimento", "atualizado_em"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    numeric_cols = [
        "quantidade_registrada",
        "valor_total_registrado",
        "preco_emissao",
        "preco_cota_b3",
        "valor_cota_vpc",
        "p_vp",
        "patrimonio_liquido",
        "volume_medio_diario",
        "total_emissoes",
        "volume_total_ofertas",
        "desconto_vs_b3",
        "desconto_vs_vp",
        "p_vp_emissao",
        "liquidez_sobre_oferta",
        "taxa_selic_data_oferta",
        "cdi_data_oferta",
        "ipca_12m_data_oferta",
        "usd_brl_data_oferta",
        "pontos_ifix_data_oferta",
        "score_priorizacao",
        "campos_criticos_preenchidos",
        "campos_criticos_total",
        "cobertura_analise_percentual",
        "rendimento_12m_historico_por_cota",
        "dy_12m_historico_sobre_emissao",
        "dy_projetado_oferta",
        "confianca_dy_projetado",
        "confianca_total",
        "confianca_dados",
        "confianca_sinais",
        "confianca_contexto",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values(["score_priorizacao", "valor_total_registrado"], ascending=[False, False])


def load_quality() -> pd.DataFrame:
    df = load_table("data_quality_report")
    if df.empty:
        return pd.DataFrame()
    df["cobertura_percentual"] = pd.to_numeric(df["cobertura_percentual"], errors="coerce").fillna(0)
    return df
