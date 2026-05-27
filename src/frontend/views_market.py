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


def render_market(ofertas: pd.DataFrame) -> None:
    st.subheader("Mesa de ofertas primarias")
    st.markdown(
        '<div class="section-note">Visao de volumes, status, coordenadores e sensibilidade ao cenario macro.</div>',
        unsafe_allow_html=True,
    )
    if ofertas.empty:
        st.warning("Base de ofertas nao encontrada. Rode `python src/main.py`.")
        return

    volume_total = ofertas["valor_total_registrado"].sum()
    total_ofertas = len(ofertas)
    ticket_medio = volume_total / total_ofertas if total_ofertas else 0
    selic_media = ofertas["taxa_selic_data_oferta"].mean()
    ifix_medio = ofertas["pontos_ifix_data_oferta"].mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Volume registrado", formatar_moeda(volume_total))
    c2.metric("Ofertas", f"{total_ofertas:,}".replace(",", "."))
    c3.metric("Ticket medio", formatar_moeda(ticket_medio))
    c4.metric("Selic media", formatar_percentual(selic_media))
    c5.metric("IFIX medio", f"{ifix_medio:.2f}" if pd.notna(ifix_medio) else "N/D")

    mensal = (
        ofertas.groupby("ano_mes", as_index=False)
        .agg(volume=("valor_total_registrado", "sum"), ofertas=("numero_processo", "count"), selic=("taxa_selic_data_oferta", "mean"), cdi=("cdi_data_oferta", "mean"))
        .sort_values("ano_mes")
    )
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=mensal["ano_mes"], y=mensal["volume"], name="Volume", marker_color=BTG_BLUE), secondary_y=False)
    fig.add_trace(go.Scatter(x=mensal["ano_mes"], y=mensal["selic"], name="Selic", line={"color": RED, "width": 3}), secondary_y=True)
    if mensal["cdi"].notna().any():
        fig.add_trace(go.Scatter(x=mensal["ano_mes"], y=mensal["cdi"], name="CDI", line={"color": TEAL, "width": 2}), secondary_y=True)
    fig.update_layout(title="Volume mensal x juros", legend_orientation="h", height=430, margin={"l": 10, "r": 10, "t": 48, "b": 20})
    fig.update_yaxes(title_text="Volume registrado", secondary_y=False)
    fig.update_yaxes(title_text="Taxa (%)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        status_volume = (
            ofertas.groupby("status_requerimento", as_index=False)
            .agg(volume=("valor_total_registrado", "sum"), ofertas=("numero_processo", "count"))
            .sort_values("volume", ascending=False)
        )
        fig_status = px.bar(status_volume, x="volume", y="status_requerimento", color="ofertas", orientation="h", color_continuous_scale="Teal", labels={"volume": "Volume", "status_requerimento": "Status"}, title="Volume por status")
        fig_status.update_layout(height=390, margin={"l": 10, "r": 10, "t": 48, "b": 20})
        st.plotly_chart(fig_status, use_container_width=True)
    with col_b:
        lideres = (
            ofertas.groupby("nome_lider", as_index=False)
            .agg(volume=("valor_total_registrado", "sum"), ofertas=("numero_processo", "count"))
            .sort_values("volume", ascending=False)
            .head(12)
        )
        fig_lider = px.bar(lideres.sort_values("volume"), x="volume", y="nome_lider", orientation="h", color_discrete_sequence=[BTG_BLUE], labels={"volume": "Volume", "nome_lider": "Coordenador"}, title="Top coordenadores")
        fig_lider.update_layout(height=390, margin={"l": 10, "r": 10, "t": 48, "b": 20})
        st.plotly_chart(fig_lider, use_container_width=True)


