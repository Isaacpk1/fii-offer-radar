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


from frontend.view_utils import _extrair_json_resposta, resposta_agente_para_texto


def render_ranking_autonomo() -> None:
    st.subheader("Ranking autonomo com diagnostico")
    if st.button("Gerar ranking agora", type="primary"):
        agente = carregar_agente()
        with st.spinner("Agente analisando ofertas..."):
            resposta = agente.invoke(
                {"input": "Use rankear_com_diagnostico(5) e retorne o JSON completo, sem markdown."}
            )

        try:
            texto = resposta_agente_para_texto(resposta)
            ranking = RankingOfertas.model_validate_json(_extrair_json_resposta(texto))

            st.info(f"**Macro:** {ranking.contexto_macro}")
            st.success(f"**Proxima acao:** {ranking.proxima_acao}")

            for i, oferta in enumerate(ranking.ofertas, 1):
                titulo = oferta.ticker or oferta.nome_emissor
                score = oferta.score_priorizacao if oferta.score_priorizacao is not None else 0
                with st.expander(f"#{i} {titulo} - Score {score:.1f}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric(
                        "Preco emissao",
                        formatar_moeda(oferta.preco_emissao) if oferta.preco_emissao is not None else "N/D",
                    )
                    c2.metric(
                        "P/VP emissao",
                        f"{oferta.p_vp_emissao:.2f}x" if oferta.p_vp_emissao is not None else "N/D",
                    )
                    c3.metric(
                        "Desconto vs B3",
                        formatar_percentual(oferta.desconto_vs_b3)
                        if oferta.desconto_vs_b3 is not None
                        else "N/D",
                    )
                    st.markdown(f"**Diagnostico:** {oferta.diagnostico}")
                    cobertura = oferta.cobertura_analise_percentual or 0
                    st.progress(max(0.0, min(cobertura / 100, 1.0)))
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            st.warning("Agente nao retornou JSON estruturado. Resposta bruta:")
            st.caption(str(exc))
            st.markdown(resposta_agente_para_texto(resposta))


def render_acoes_autonomas(inteligencia: pd.DataFrame) -> None:
    st.subheader("Acoes do agente")
    if inteligencia.empty or "numero_processo" not in inteligencia.columns:
        st.info("Base de inteligencia indisponivel para executar acoes.")
        return

    processos = inteligencia["numero_processo"].dropna().astype(str).drop_duplicates().tolist()
    if not processos:
        st.info("Nenhuma oferta disponivel para acoes autonomas.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Gerar brief de oferta**")
        processo_sel = st.selectbox("Selecionar oferta", processos, key="brief_proc")
        if st.button("Gerar brief", key="btn_brief"):
            agente = carregar_agente()
            with st.spinner("Agente gerando brief..."):
                resposta = agente.invoke(
                    {
                        "input": (
                            f"Gere o brief completo para o processo {processo_sel}. "
                            "Use gerar_brief_oferta e considere macro atual e noticias de contexto."
                        )
                    }
                )
            st.success(resposta_agente_para_texto(resposta))

    with col2:
        st.markdown("**Registrar decisao**")
        processo_dec = st.selectbox("Oferta", processos, key="dec_proc")
        decisao = st.radio("Decisao", ["aprovar", "rejeitar", "pendente"], horizontal=True)
        justificativa = st.text_area("Justificativa", key="dec_justificativa")
        if st.button("Registrar", key="btn_decisao"):
            if not justificativa.strip():
                st.warning("Informe uma justificativa antes de registrar.")
                return
            agente = carregar_agente()
            with st.spinner("Registrando decisao..."):
                resposta = agente.invoke(
                    {
                        "input": (
                            f"Registre a decisao '{decisao}' para o processo {processo_dec}. "
                            f"Justificativa: {justificativa}. Use registrar_decisao_analista."
                        )
                    }
                )
            st.success(resposta_agente_para_texto(resposta))


def render_alertas_autonomos() -> None:
    st.subheader("Alertas autonomos")
    if not ALERTAS_DIR.exists() or not list(ALERTAS_DIR.glob("*.json")):
        st.info("Nenhum alerta autonomo ainda. Execute: `python src/ai_core/autonomous_runner.py`")
        return

    arquivos = sorted(ALERTAS_DIR.glob("triagem_diaria_*.json"), reverse=True)
    if not arquivos:
        st.info("Nenhuma triagem diaria encontrada ainda.")
        return

    alerta = json.loads(arquivos[0].read_text(encoding="utf-8"))
    resultado = alerta.get("resultado", {})
    st.markdown(f"*Ultima triagem: {str(alerta.get('timestamp', ''))[:16]}*")

    alertas_urgentes = resultado.get("alertas_urgentes", []) if isinstance(resultado, dict) else []
    if alertas_urgentes:
        st.error(f"**{len(alertas_urgentes)} alerta(s) urgente(s)**")
        for alerta_item in alertas_urgentes:
            st.markdown(f"- {alerta_item}")
    else:
        st.success("Nenhum alerta urgente na ultima triagem.")

    if isinstance(resultado, dict) and resultado.get("resumo_mercado"):
        st.markdown(f"**Resumo de mercado:** {resultado['resumo_mercado']}")
    if isinstance(resultado, dict) and resultado.get("acao_recomendada"):
        st.info(f"**Acao recomendada:** {resultado['acao_recomendada']}")


def render_confidence_caption_from_text(texto: object) -> None:
    texto = resposta_agente_para_texto(texto)
    match = re.search(
        r"Confianca da analise:\s*([A-Za-zÀ-ÿ]+)\s*\((\d+(?:[.,]\d+)?)/100\)",
        texto,
        flags=re.IGNORECASE,
    )
    if not match:
        return

    nivel = match.group(1)
    score = match.group(2).replace(",", ".")
    marcador = {"Alta": "Verde", "Media": "Amarela", "Média": "Amarela", "Baixa": "Vermelha", "Insuficiente": "Cinza"}.get(
        nivel,
        "Neutra",
    )
    st.caption(f"Confianca reportada pelo agente: {nivel} ({score}/100) - {marcador}")


def render_copilot(ofertas: pd.DataFrame) -> None:
    st.subheader("Copiloto analitico")
    st.markdown(
        '<div class="section-note">Gera leitura interpretativa usando o warehouse, a tese da oferta, qualidade dos dados e ferramentas macro.</div>',
        unsafe_allow_html=True,
    )
    prompt_sugerido = st.selectbox(
        "Perguntas sugeridas",
        [
            "Quais ofertas primarias devem ser priorizadas para analise e por que?",
            "Compare preco de emissao contra B3 e VP/C, destacando riscos de liquidez.",
            "Mostre ofertas com DY projetado documentado e boa confianca de extracao.",
            "Quais campos faltam para melhorar a decisao sobre ofertas primarias?",
        ],
    )
    if "mensagens" not in st.session_state:
        st.session_state.mensagens = []
    for msg in st.session_state.mensagens:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pergunta = st.chat_input("Pergunte sobre ofertas, DY projetado, coordenadores, macro, FIIs ou qualidade da base...")
    if st.button("Usar pergunta sugerida"):
        pergunta = prompt_sugerido
    if pergunta:
        st.session_state.mensagens.append({"role": "user", "content": pergunta})
        with st.chat_message("user"):
            st.markdown(pergunta)
        with st.chat_message("assistant"):
            with st.spinner("Analisando dados e contexto..."):
                try:
                    resposta = carregar_agente().invoke({"input": pergunta})
                    texto = resposta_agente_para_texto(resposta)
                    render_confidence_caption_from_text(texto)
                    st.markdown(texto)
                    st.session_state.mensagens.append({"role": "assistant", "content": texto})
                except Exception as exc:
                    st.error(f"Nao foi possivel executar o agente: {exc}")

    st.divider()
    inteligencia = load_table("oferta_inteligencia")
    render_ranking_autonomo()
    st.divider()
    render_acoes_autonomas(inteligencia)
    st.divider()
    render_alertas_autonomos()
