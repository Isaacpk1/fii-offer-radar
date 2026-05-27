import json
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from pydantic import ValidationError

from ai_core.tools import RankingOfertas
from frontend.agent_session import carregar_agente
from frontend.components import tabela_interativa
from frontend.config import AMBER, BTG_BLUE, GREEN, MUTED, RED, TABLE_LABELS, TAPI_STEPS, TEAL
from frontend.data import get_connection, load_table
from frontend.formatters import coverage_color, formatar_moeda, formatar_percentual, status_class


ALERTAS_DIR = Path("src/data/alertas_autonomos")


def render_fii_compare(metricas: pd.DataFrame) -> None:
    st.subheader("Suporte do fundo")
    st.markdown(
        '<div class="section-note">Esta aba apoia a decisao da oferta. Ela nao tenta ser um screener completo de FIIs.</div>',
        unsafe_allow_html=True,
    )
    if metricas.empty:
        st.warning("Base de metricas nao encontrada. Rode `python src/main.py`.")
        return

    with_data = metricas.copy()
    id_col = "ticker" if "ticker" in with_data.columns and with_data["ticker"].notna().any() else "cnpj"
    opcoes = with_data[id_col].dropna().astype(str).sort_values().unique().tolist()
    selecionados = st.multiselect("Selecione ate 6 FIIs", opcoes, default=opcoes[:6], max_selections=6)
    if not selecionados:
        st.info("Selecione ao menos um fundo para abrir a comparacao.")
        return

    df_sel = with_data[with_data[id_col].astype(str).isin(selecionados)].copy()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fundos selecionados", len(df_sel))
    c2.metric("Com preco B3", int(df_sel["preco_cota"].notna().sum()) if "preco_cota" in df_sel else 0)
    c3.metric("Com preco emissao", int(df_sel["preco_emissao"].notna().sum()) if "preco_emissao" in df_sel else 0)
    c4.metric("Com P/VP mercado", int(df_sel["p_vp"].notna().sum()) if "p_vp" in df_sel else 0)

    col_price, col_liq = st.columns(2)
    with col_price:
        price_df = df_sel[[c for c in [id_col, "preco_cota", "preco_emissao"] if c in df_sel.columns]].melt(id_vars=id_col, value_vars=[c for c in ["preco_cota", "preco_emissao"] if c in df_sel.columns], var_name="metrica", value_name="valor").dropna(subset=["valor"])
        if not price_df.empty:
            fig = px.bar(price_df, x=id_col, y="valor", color="metrica", barmode="group", title="Preco B3 vs preco de emissao", labels={"valor": "Preco", id_col: "FII"}, color_discrete_map={"preco_cota": BTG_BLUE, "preco_emissao": TEAL})
            fig.update_layout(height=390, margin={"l": 10, "r": 10, "t": 48, "b": 20})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Preco de mercado/emissao sem cobertura para os selecionados.")
    with col_liq:
        if "volume_medio_diario" in df_sel.columns and df_sel["volume_medio_diario"].notna().any():
            fig = px.bar(df_sel.dropna(subset=["volume_medio_diario"]).sort_values("volume_medio_diario"), x="volume_medio_diario", y=id_col, orientation="h", title="Liquidez media diaria", color_discrete_sequence=[BTG_BLUE], labels={"volume_medio_diario": "Volume medio", id_col: "FII"})
            fig.update_layout(height=390, margin={"l": 10, "r": 10, "t": 48, "b": 20})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Liquidez ainda sem cobertura para os selecionados.")

    table_cols = [id_col, "cnpj", "patrimonio_liquido", "valor_cota_vpc", "preco_cota", "p_vp", "preco_emissao", "desconto_oferta_vp", "desconto_oferta_b3", "volume_medio_diario", "total_emissoes", "volume_total_ofertas", "coordenador_principal", "numero_cotistas", "dividend_yield_12m", "status_viabilidade_oferta"]
    st.markdown("#### Tabela comparativa")
    tabela_interativa(df_sel[[c for c in table_cols if c in df_sel.columns]], "fii_compare")


