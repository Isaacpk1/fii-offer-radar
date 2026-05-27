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


def render_quality(quality: pd.DataFrame) -> None:
    st.subheader("Qualidade das tabelas")
    st.markdown(
        '<div class="section-note">Cobertura por tabela e coluna. Aqui fica claro o que sustenta analise e o que ainda precisa de fonte.</div>',
        unsafe_allow_html=True,
    )
    if quality.empty:
        st.info("Relatorio de qualidade indisponivel. Gere o warehouse com `python src/database/build_database.py`.")
        return

    resumo = (
        quality.groupby("tabela", as_index=False)
        .agg(campos=("coluna", "count"), cobertura_media=("cobertura_percentual", "mean"), sem_cobertura=("cobertura_percentual", lambda s: int((s == 0).sum())))
        .sort_values("cobertura_media", ascending=False)
    )
    cols = st.columns(3)
    cols[0].metric("Tabelas", resumo["tabela"].nunique())
    cols[1].metric("Cobertura media", f"{resumo['cobertura_media'].mean():.1f}%")
    cols[2].metric("Campos zerados", int(resumo["sem_cobertura"].sum()))

    for _, row in resumo.iterrows():
        color = coverage_color(row["cobertura_media"])
        st.markdown(
            f"""
            <div style="margin: 12px 0 4px 0;">
                <b>{TABLE_LABELS.get(row["tabela"], row["tabela"])}</b>
                <span class="small-muted">({row["tabela"]}) - {row["campos"]} campos, {row["sem_cobertura"]} sem cobertura</span>
            </div>
            <div class="coverage-track">
                <div class="coverage-fill" style="width: {row["cobertura_media"]:.1f}%; background: {color};"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("#### Detalhe por coluna")
    tabela_interativa(quality.sort_values(["tabela", "cobertura_percentual"]), "quality_detail")


def render_warehouse_explorer() -> None:
    st.subheader("Explorador do warehouse")
    st.markdown(
        '<div class="section-note">Todas as tabelas do banco local em um lugar, com filtro, ordenacao e paginacao.</div>',
        unsafe_allow_html=True,
    )
    if get_connection() is None:
        st.warning("Warehouse DuckDB nao encontrado. Rode `python src/database/build_database.py`.")
        return

    table = st.selectbox("Tabela", list(TABLE_LABELS.keys()), format_func=lambda value: f"{TABLE_LABELS.get(value, value)} ({value})")
    df = load_table(table)
    c1, c2, c3 = st.columns(3)
    c1.metric("Linhas", f"{len(df):,}".replace(",", "."))
    c2.metric("Colunas", len(df.columns))
    c3.metric("Fonte", "DuckDB")

    query = st.text_input("Busca rapida na tabela", placeholder="Digite parte de um ticker, CNPJ, processo ou nome")
    if query and not df.empty:
        mask = df.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
        df = df[mask]
    tabela_interativa(df, f"warehouse_{table}", height=520)


