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


def render_tapi_alignment(
    quality: pd.DataFrame,
    ofertas: pd.DataFrame,
    metricas: pd.DataFrame,
    inteligencia: pd.DataFrame,
) -> None:
    st.subheader("Aderencia ao projeto TAPI")
    st.markdown(
        '<div class="section-note">Leitura estatica do escopo: coleta, documentos, extracao semantica e tese da oferta.</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    for idx, step in enumerate(TAPI_STEPS, start=1):
        with cols[(idx - 1) % 3]:
            st.markdown(
                f"""
                <div class="play-step">
                    <span class="play-step-number">{idx}</span>
                    <span class="play-step-title">{step["titulo"]}</span>
                    <div style="margin-top: 8px;">
                        <span class="status-pill {status_class(step["status"])}">{step["status"]}</span>
                    </div>
                    <div class="play-step-text">{step["texto"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ofertas analisaveis", f"{len(ofertas):,}".replace(",", "."))
    c2.metric("Teses de oferta", f"{len(inteligencia):,}".replace(",", "."))
    c3.metric("FIIs no suporte", f"{len(metricas):,}".replace(",", "."))
    sem_cobertura = len(quality[quality["cobertura_percentual"] == 0]) if not quality.empty else 0
    c4.metric("Campos sem cobertura", sem_cobertura)

    rows = [
        ("Ofertas de FIIs", "OK", "Base CVM estruturada, com volumes, coordenador, status e macro."),
        ("PDFs de oferta", "OK", "Documentos catalogados por processo e prontos para extracao."),
        ("DY historico", "Suporte", "Rendimento dos informes fica separado do DY da nova emissao."),
        ("DY projetado", "Em evolucao", "Campo vem de documentos de oferta via regex + LangChain."),
        ("Preco vs B3/VP", "OK", "Comparacao calculada quando ticker e VP/C estao disponiveis."),
        ("Interface executiva", "OK", "Dashboard prioriza decisao sobre ofertas primarias."),
    ]
    tabela_interativa(pd.DataFrame(rows, columns=["Modulo", "Status", "Leitura"]), "tapi_status", height=260)


