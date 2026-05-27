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
from frontend.config import AMBER, BTG_BLUE, GREEN, MUTED, RED, TABLE_LABELS, TEAL
from frontend.data import get_connection, load_table
from frontend.formatters import coverage_color, formatar_moeda, formatar_percentual, status_class


ALERTAS_DIR = Path("src/data/alertas_autonomos")


from frontend.view_utils import render_confidence_gauge


def render_offer_compare(ofertas: pd.DataFrame) -> None:
    st.subheader("Comparador de ofertas")
    st.markdown(
        '<div class="section-note">Escolha ofertas e compare volume, preco de emissao, status e contexto macro.</div>',
        unsafe_allow_html=True,
    )
    if ofertas.empty:
        st.warning("Nenhuma oferta disponivel.")
        return

    opcoes = ofertas.assign(rotulo=lambda df: df["numero_processo"].astype(str) + " | " + df["nome_emissor"].str.slice(0, 70))
    selecionadas = st.multiselect("Ofertas para comparar", opcoes["rotulo"].tolist(), default=opcoes["rotulo"].head(5).tolist(), max_selections=12)
    df_comp = opcoes[opcoes["rotulo"].isin(selecionadas)].copy()
    if df_comp.empty:
        st.info("Selecione ao menos uma oferta.")
        return

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(df_comp.sort_values("valor_total_registrado"), x="valor_total_registrado", y="numero_processo", color="nome_lider", orientation="h", hover_data=["nome_emissor", "status_requerimento", "publico_alvo"], title="Tamanho da emissao", labels={"valor_total_registrado": "Volume", "numero_processo": "Processo"})
        fig.update_layout(height=420, margin={"l": 10, "r": 10, "t": 48, "b": 20})
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.scatter(df_comp, x="taxa_selic_data_oferta", y="valor_total_registrado", size="valor_total_registrado", color="status_requerimento", hover_data=["numero_processo", "nome_emissor", "preco_emissao"], title="Volume x Selic na oferta", labels={"taxa_selic_data_oferta": "Selic (%)", "valor_total_registrado": "Volume"})
        fig.update_layout(height=420, margin={"l": 10, "r": 10, "t": 48, "b": 20})
        st.plotly_chart(fig, use_container_width=True)

    cols = ["numero_processo", "data_requerimento", "nome_emissor", "nome_lider", "tipo_oferta", "valor_total_registrado", "preco_emissao", "status_requerimento", "publico_alvo", "taxa_selic_data_oferta", "cdi_data_oferta", "ipca_12m_data_oferta", "usd_brl_data_oferta", "pontos_ifix_data_oferta"]
    tabela_interativa(df_comp[[c for c in cols if c in df_comp.columns]], "ofertas_compare")


def render_offer_intelligence(inteligencia: pd.DataFrame) -> None:
    st.subheader("Tese da oferta primaria")
    st.markdown(
        '<div class="section-note">DY projetado da oferta fica separado do yield historico do fundo. Quando existir, ele vem do documento de oferta.</div>',
        unsafe_allow_html=True,
    )
    if inteligencia.empty:
        st.warning("Tabela `oferta_inteligencia` nao encontrada. Rode `python src/database/build_database.py`.")
        return

    col_f1, col_f2, col_f3, col_f4 = st.columns([1.15, 0.8, 0.9, 0.9])
    with col_f1:
        leituras = sorted(inteligencia["leitura_priorizacao"].dropna().unique())
        leitura_sel = st.multiselect("Prioridade", leituras, default=leituras)
    with col_f2:
        min_score = st.slider("Score minimo", 0, 100, 0)
    with col_f3:
        apenas_com_b3 = st.checkbox("Apenas com comparavel B3", value=False)
    with col_f4:
        apenas_com_dy = st.checkbox("Apenas com DY projetado", value=False)

    df = inteligencia[inteligencia["score_priorizacao"].fillna(0) >= min_score].copy()
    if leitura_sel:
        df = df[df["leitura_priorizacao"].isin(leitura_sel)]
    if apenas_com_b3:
        df = df[df["preco_cota_b3"].notna()]
    if apenas_com_dy and "dy_projetado_oferta" in df:
        df = df[df["dy_projetado_oferta"].notna()]

    if df.empty:
        st.info("Nenhuma oferta encontrada para os filtros de tese.")
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Teses filtradas", f"{len(df):,}".replace(",", "."))
    c2.metric("Score medio", f"{df['score_priorizacao'].mean():.1f}")
    c3.metric("Com B3", int(df["preco_cota_b3"].notna().sum()))
    c4.metric("Com DY projetado", int(df["dy_projetado_oferta"].notna().sum()) if "dy_projetado_oferta" in df else 0)
    c5.metric("Cobertura media", f"{df['cobertura_analise_percentual'].mean():.1f}%")
    if "confianca_total" in df.columns:
        st.caption(f"Confianca auditavel media: {df['confianca_total'].mean():.1f}/100")

    col_a, col_b = st.columns(2)
    with col_a:
        top = df.sort_values("score_priorizacao", ascending=False).head(20)
        fig = px.bar(
            top.sort_values("score_priorizacao"),
            x="score_priorizacao",
            y="numero_processo",
            color="leitura_priorizacao",
            orientation="h",
            hover_data=["ticker", "nome_emissor", "preco_emissao", "dy_projetado_oferta", "preco_cota_b3", "desconto_vs_b3"],
            title="Ranking de priorizacao para analise",
            labels={"score_priorizacao": "Score", "numero_processo": "Processo"},
            color_discrete_map={"Prioridade alta para analise": GREEN, "Prioridade media": TEAL, "Prioridade baixa": AMBER, "Monitorar apenas": MUTED},
        )
        fig.update_layout(height=470, margin={"l": 10, "r": 10, "t": 48, "b": 20})
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        comparaveis = df[df["desconto_vs_b3"].notna()].copy()
        if not comparaveis.empty:
            comparaveis["desconto_vs_b3_pct"] = comparaveis["desconto_vs_b3"] * 100
            fig = px.scatter(
                comparaveis,
                x="desconto_vs_b3_pct",
                y="dy_projetado_oferta",
                size="valor_total_registrado",
                color="sinal_preco_b3",
                hover_data=["numero_processo", "ticker", "nome_emissor", "score_priorizacao", "liquidez_sobre_oferta"],
                title="Preco vs B3 e DY projetado",
                labels={"desconto_vs_b3_pct": "Desconto/premio vs B3 (%)", "dy_projetado_oferta": "DY projetado"},
            )
            fig.add_vline(x=0, line_dash="dash", line_color="#8A94A6")
            fig.update_layout(height=470, margin={"l": 10, "r": 10, "t": 48, "b": 20})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma oferta filtrada tem comparavel B3.")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        sinais = df.groupby(["sinal_preco_b3", "leitura_priorizacao"], as_index=False).agg(ofertas=("numero_processo", "count"))
        fig = px.bar(sinais, x="sinal_preco_b3", y="ofertas", color="leitura_priorizacao", title="Distribuicao dos sinais de preco", labels={"sinal_preco_b3": "Sinal", "ofertas": "Ofertas"})
        fig.update_layout(height=360, margin={"l": 10, "r": 10, "t": 48, "b": 80}, xaxis_tickangle=-25)
        st.plotly_chart(fig, use_container_width=True)
    with col_s2:
        dy_df = df[df["dy_projetado_oferta"].notna()].copy()
        if not dy_df.empty:
            dy_df["dy_projetado_pct"] = dy_df["dy_projetado_oferta"] * 100
            fig = px.bar(dy_df.sort_values("dy_projetado_pct").tail(20), x="dy_projetado_pct", y="numero_processo", orientation="h", color="confianca_dy_projetado", color_continuous_scale="Teal", title="DY projetado extraido de documentos", labels={"dy_projetado_pct": "DY projetado (%)", "numero_processo": "Processo"})
            fig.update_layout(height=360, margin={"l": 10, "r": 10, "t": 48, "b": 20})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma oferta filtrada tem DY projetado extraido.")

    st.markdown("#### Ficha de decisao")
    cols = [
        "numero_processo", "ticker", "nome_emissor", "nome_lider", "data_requerimento", "status_requerimento",
        "valor_total_registrado", "preco_emissao", "dy_projetado_oferta", "confianca_dy_projetado",
        "dy_12m_historico_sobre_emissao", "rendimento_12m_historico_por_cota", "meses_historico_utilizados",
        "preco_cota_b3", "desconto_vs_b3", "valor_cota_vpc", "p_vp_emissao", "desconto_vs_vp",
        "volume_medio_diario", "sinal_preco_b3", "sinal_preco_vp", "sinal_liquidez", "sinal_historico",
        "score_priorizacao", "leitura_priorizacao", "cobertura_analise_percentual",
        "confianca_total", "confianca_nivel", "confianca_dados", "confianca_sinais", "confianca_contexto",
        "confianca_resumo", "dados_ausentes_criticos",
    ]
    selected = tabela_interativa(df[[c for c in cols if c in df.columns]], "oferta_inteligencia", height=460)
    if selected:
        st.markdown("#### Oferta selecionada")
        render_confidence_gauge(selected[0])
        st.json(selected[0])


