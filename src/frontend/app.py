from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from langchain_classic.memory import ConversationBufferMemory
from plotly.subplots import make_subplots

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
except ImportError:
    AgGrid = None
    GridOptionsBuilder = None
    GridUpdateMode = None


SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_DIR.parent
PROCESSED_DATA_PATH = SRC_DIR / "data" / "processed" / "ofertas_fiis_pronto_para_ia.csv"
STATUS_ALERTS_PATH = SRC_DIR / "data" / "processed" / "status_monitor_alerts.json"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_core.agent import inicializar_agente_analista


st.set_page_config(
    page_title="BTG Pactual | CVM 160 Intelligence",
    page_icon=":bar_chart:",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main-title { font-size: 32px; font-weight: 700; color: #002F6C; }
    .subtitle { font-size: 16px; color: #4A5568; margin-bottom: 20px; }
    .stMetric { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 14px; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="main-title">CVM 160 Analytics Hub | BTG Pactual</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="subtitle">Analise comparativa de ofertas primarias de Fundos de Investimento Imobiliario com dados reais da CVM, Selic, IPCA, CDI, cambio e IFIX.</p>',
    unsafe_allow_html=True,
)
st.divider()


def formatar_moeda(valor: float) -> str:
    if pd.isna(valor):
        return "R$ 0,00"
    if abs(valor) >= 1_000_000_000:
        return f"R$ {valor / 1_000_000_000:.2f} bi"
    if abs(valor) >= 1_000_000:
        return f"R$ {valor / 1_000_000:.2f} mi"
    return f"R$ {valor:,.2f}"


def validar_colunas(df: pd.DataFrame) -> None:
    colunas_obrigatorias = {
        "Numero_Processo",
        "Data_requerimento",
        "Nome_Emissor",
        "Nome_Lider",
        "Tipo_Oferta",
        "Valor_Total_Registrado",
        "Status_Requerimento",
        "Publico_alvo",
        "Taxa_Selic_Data_Oferta",
        "Pontos_IFIX_Data_Oferta",
    }
    ausentes = sorted(colunas_obrigatorias.difference(df.columns))
    if ausentes:
        st.error(
            "A base processada nao tem todas as colunas esperadas: "
            + ", ".join(ausentes)
        )
        st.stop()


def colunas_macro_disponiveis(df: pd.DataFrame) -> list[str]:
    candidatas = [
        "Taxa_Selic_Data_Oferta",
        "CDI_Data_Oferta",
        "IPCA_12m_Data_Oferta",
        "USD_BRL_Data_Oferta",
        "Pontos_IFIX_Data_Oferta",
    ]
    return [col for col in candidatas if col in df.columns and df[col].notna().any()]


def exibir_grade_interativa(df: pd.DataFrame, key: str):
    if AgGrid is None:
        st.info("Instale `streamlit-aggrid` para filtros avancados por coluna. Usando tabela nativa.")
        st.dataframe(df, use_container_width=True, hide_index=True)
        return []

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(filter=True, sortable=True, resizable=True)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    grid_options = gb.build()

    response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        use_container_width=True,
        key=key,
    )
    selected = response.get("selected_rows", [])
    if isinstance(selected, pd.DataFrame):
        return selected.to_dict("records")
    return selected or []


@st.cache_data(show_spinner=False)
def carregar_ofertas_fiis() -> pd.DataFrame:
    if not PROCESSED_DATA_PATH.exists():
        st.error(
            "Base processada nao encontrada. Rode `python src/main.py` para gerar "
            f"`{PROCESSED_DATA_PATH.relative_to(PROJECT_ROOT)}`."
        )
        st.stop()

    df = pd.read_csv(PROCESSED_DATA_PATH, sep=";", encoding="utf-8")
    validar_colunas(df)

    df["Data_requerimento"] = pd.to_datetime(df["Data_requerimento"], errors="coerce")
    df["Valor_Total_Registrado"] = pd.to_numeric(
        df["Valor_Total_Registrado"], errors="coerce"
    ).fillna(0)

    for coluna in [
        "Taxa_Selic_Data_Oferta",
        "Pontos_IFIX_Data_Oferta",
        "IPCA_12m_Data_Oferta",
        "CDI_Data_Oferta",
        "USD_BRL_Data_Oferta",
    ]:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    df = df.dropna(subset=["Data_requerimento"]).copy()
    df["Ano_Mes"] = df["Data_requerimento"].dt.to_period("M").astype(str)
    df["Ano"] = df["Data_requerimento"].dt.year
    df["Trimestre"] = df["Data_requerimento"].dt.to_period("Q").astype(str)

    for coluna in ["Nome_Emissor", "Nome_Lider", "Tipo_Oferta", "Status_Requerimento", "Publico_alvo"]:
        df[coluna] = df[coluna].fillna("Nao informado").astype(str)

    return df.sort_values("Data_requerimento", ascending=False)


def carregar_agente():
    if "agent_memory" not in st.session_state:
        st.session_state.agent_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
        )
    if "agente" not in st.session_state:
        st.session_state.agente = inicializar_agente_analista(
            memory=st.session_state.agent_memory
        )
    return st.session_state.agente


df_ofertas = carregar_ofertas_fiis()

with st.sidebar:
    st.header("Filtros")
    if STATUS_ALERTS_PATH.exists():
        alertas_status = pd.read_json(STATUS_ALERTS_PATH)
        if not alertas_status.empty:
            st.warning(f"{len(alertas_status)} mudanca(s) de status detectada(s).")
            with st.expander("Ver alertas de status"):
                st.dataframe(alertas_status, use_container_width=True, hide_index=True)

    data_min = df_ofertas["Data_requerimento"].min().date()
    data_max = df_ofertas["Data_requerimento"].max().date()
    periodo = st.date_input(
        "Periodo de requerimento",
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max,
    )

    lideres = sorted(df_ofertas["Nome_Lider"].dropna().unique())
    status = sorted(df_ofertas["Status_Requerimento"].dropna().unique())
    publicos = sorted(df_ofertas["Publico_alvo"].dropna().unique())

    lideres_sel = st.multiselect("Coordenador lider", lideres)
    status_sel = st.multiselect("Status", status)
    publicos_sel = st.multiselect("Publico-alvo", publicos)


df_filtrado = df_ofertas.copy()
if isinstance(periodo, tuple) and len(periodo) == 2:
    inicio, fim = periodo
    df_filtrado = df_filtrado[
        (df_filtrado["Data_requerimento"].dt.date >= inicio)
        & (df_filtrado["Data_requerimento"].dt.date <= fim)
    ]

if lideres_sel:
    df_filtrado = df_filtrado[df_filtrado["Nome_Lider"].isin(lideres_sel)]
if status_sel:
    df_filtrado = df_filtrado[df_filtrado["Status_Requerimento"].isin(status_sel)]
if publicos_sel:
    df_filtrado = df_filtrado[df_filtrado["Publico_alvo"].isin(publicos_sel)]

if df_filtrado.empty:
    st.warning("Nenhuma oferta encontrada para os filtros selecionados.")
    st.stop()


tab_mercado, tab_macro, tab_comparacao, tab_lideres, tab_base, tab_copiloto = st.tabs(
    [
        "Visao de Mercado",
        "Macro",
        "Comparacao de Ofertas",
        "Coordenadores",
        "Base CVM",
        "Copiloto de IA",
    ]
)


with tab_mercado:
    st.subheader("Panorama das ofertas de FIIs")

    volume_total = df_filtrado["Valor_Total_Registrado"].sum()
    total_ofertas = len(df_filtrado)
    ticket_medio = volume_total / total_ofertas if total_ofertas else 0
    selic_media = df_filtrado["Taxa_Selic_Data_Oferta"].mean()
    ifix_medio = df_filtrado["Pontos_IFIX_Data_Oferta"].mean()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Volume registrado", formatar_moeda(volume_total))
    col2.metric("Ofertas mapeadas", f"{total_ofertas:,}".replace(",", "."))
    col3.metric("Ticket medio", formatar_moeda(ticket_medio))
    col4.metric("Selic media", f"{selic_media:.2f}%" if pd.notna(selic_media) else "N/D")
    col5.metric("IFIX medio", f"{ifix_medio:.2f}" if pd.notna(ifix_medio) else "N/D")

    st.divider()

    volume_mensal = (
        df_filtrado.groupby("Ano_Mes", as_index=False)
        .agg(
            Volume=("Valor_Total_Registrado", "sum"),
            Ofertas=("Numero_Processo", "count"),
            Selic_media=("Taxa_Selic_Data_Oferta", "mean"),
        )
        .sort_values("Ano_Mes")
    )

    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(
        go.Bar(
            x=volume_mensal["Ano_Mes"],
            y=volume_mensal["Volume"],
            name="Volume registrado",
            marker_color="#002F6C",
        ),
        secondary_y=False,
    )
    fig_dual.add_trace(
        go.Scatter(
            x=volume_mensal["Ano_Mes"],
            y=volume_mensal["Selic_media"],
            name="Selic media",
            line={"color": "#E24B4A", "width": 3},
        ),
        secondary_y=True,
    )
    fig_dual.update_yaxes(title_text="Volume registrado", secondary_y=False)
    fig_dual.update_yaxes(title_text="Selic media (%)", secondary_y=True)
    fig_dual.update_layout(title="Volume mensal x Selic media", legend_orientation="h")
    st.plotly_chart(fig_dual, use_container_width=True)

    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        colunas_corr = ["Valor_Total_Registrado"] + colunas_macro_disponiveis(df_filtrado)
        matriz_corr = (
            df_filtrado[colunas_corr]
            .corr(numeric_only=True)
            .dropna(how="all")
            .dropna(axis=1, how="all")
        )
        if matriz_corr.shape[0] >= 2:
            fig_corr = px.imshow(
                matriz_corr,
                text_auto=".2f",
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
                title="Correlacao macro x mercado",
            )
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("Dados insuficientes para calcular a matriz de correlacao.")

    with col_graf2:
        status_volume = (
            df_filtrado.groupby("Status_Requerimento", as_index=False)
            .agg(Volume=("Valor_Total_Registrado", "sum"))
            .sort_values("Volume", ascending=False)
        )
        fig_status = px.pie(
            status_volume,
            names="Status_Requerimento",
            values="Volume",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig_status, use_container_width=True)

    col_graf3, col_graf4 = st.columns(2)
    with col_graf3:
        fig_selic = px.scatter(
            df_filtrado,
            x="Taxa_Selic_Data_Oferta",
            y="Valor_Total_Registrado",
            color="Publico_alvo",
            hover_data=["Numero_Processo", "Nome_Emissor", "Nome_Lider"],
            labels={
                "Taxa_Selic_Data_Oferta": "Selic na data da oferta (%)",
                "Valor_Total_Registrado": "Volume registrado",
            },
        )
        st.plotly_chart(fig_selic, use_container_width=True)

    with col_graf4:
        publico_volume = (
            df_filtrado.groupby("Publico_alvo", as_index=False)
            .agg(Volume=("Valor_Total_Registrado", "sum"), Ofertas=("Numero_Processo", "count"))
            .sort_values("Volume", ascending=False)
        )
        fig_publico = px.bar(
            publico_volume,
            x="Publico_alvo",
            y="Volume",
            color="Ofertas",
            labels={"Publico_alvo": "Publico-alvo", "Volume": "Volume registrado"},
            color_continuous_scale="Teal",
        )
        st.plotly_chart(fig_publico, use_container_width=True)

    if st.button("Gerar relatorio executivo", type="primary"):
        top_lideres = (
            df_filtrado.groupby("Nome_Lider")["Valor_Total_Registrado"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
        )
        status_dist = (
            df_filtrado.groupby("Status_Requerimento")["Valor_Total_Registrado"]
            .sum()
            .sort_values(ascending=False)
        )
        prompt_relatorio = f"""
        Gere um relatorio executivo em tres paragrafos sobre o recorte filtrado de ofertas de FIIs.
        KPIs: volume total {formatar_moeda(volume_total)}, total de ofertas {total_ofertas},
        ticket medio {formatar_moeda(ticket_medio)}, Selic media {selic_media:.2f}%.
        Top coordenadores por volume: {top_lideres.to_dict()}.
        Distribuicao por status: {status_dist.to_dict()}.
        Estruture como: cenario macro, performance de mercado e destaques/anomalias.
        """
        with st.spinner("Gerando relatorio com o copiloto..."):
            try:
                resposta = carregar_agente().invoke({"input": prompt_relatorio})
                st.session_state["relatorio_executivo"] = resposta.get("output", str(resposta))
            except Exception as e:
                st.error(f"Nao foi possivel gerar relatorio: {e}")

    if "relatorio_executivo" in st.session_state:
        st.markdown(st.session_state["relatorio_executivo"])


with tab_macro:
    st.subheader("Painel macro comparativo")
    st.caption("Volume de ofertas no eixo esquerdo e indicadores macro no eixo direito.")

    agg_map = {
        "Volume": ("Valor_Total_Registrado", "sum"),
        "Selic": ("Taxa_Selic_Data_Oferta", "mean"),
    }
    if "CDI_Data_Oferta" in df_filtrado.columns:
        agg_map["CDI"] = ("CDI_Data_Oferta", "mean")
    if "IPCA_12m_Data_Oferta" in df_filtrado.columns:
        agg_map["IPCA_12m"] = ("IPCA_12m_Data_Oferta", "mean")
    if "USD_BRL_Data_Oferta" in df_filtrado.columns:
        agg_map["USD_BRL"] = ("USD_BRL_Data_Oferta", "mean")

    macro_mensal = (
        df_filtrado.groupby("Ano_Mes", as_index=False)
        .agg(**agg_map)
        .sort_values("Ano_Mes")
    )
    fig_macro = make_subplots(specs=[[{"secondary_y": True}]])
    fig_macro.add_trace(
        go.Bar(
            x=macro_mensal["Ano_Mes"],
            y=macro_mensal["Volume"],
            name="Volume",
            marker_color="#002F6C",
        ),
        secondary_y=False,
    )
    for coluna, cor in [("Selic", "#E24B4A"), ("CDI", "#008080"), ("IPCA_12m", "#7A4DD8"), ("USD_BRL", "#D98C00")]:
        if coluna in macro_mensal and macro_mensal[coluna].notna().any():
            fig_macro.add_trace(
                go.Scatter(
                    x=macro_mensal["Ano_Mes"],
                    y=macro_mensal[coluna],
                    name=coluna,
                    line={"color": cor},
                ),
                secondary_y=True,
            )
    fig_macro.update_yaxes(title_text="Volume registrado", secondary_y=False)
    fig_macro.update_yaxes(title_text="Indicadores macro", secondary_y=True)
    fig_macro.update_layout(legend_orientation="h")
    st.plotly_chart(fig_macro, use_container_width=True)

    macro_cols = colunas_macro_disponiveis(df_filtrado)
    if macro_cols:
        st.dataframe(
            df_filtrado[["Data_requerimento", "Numero_Processo", "Valor_Total_Registrado"] + macro_cols],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Rode o pipeline atualizado para preencher IPCA, CDI e cambio.")


with tab_comparacao:
    st.subheader("Comparacao direta entre ofertas de FIIs")

    opcoes = (
        df_filtrado.assign(
            Rotulo=lambda df: df["Numero_Processo"]
            + " | "
            + df["Nome_Emissor"].str.slice(0, 70)
        )
        .sort_values("Data_requerimento", ascending=False)
    )

    selecionadas = st.multiselect(
        "Selecione ofertas para comparar",
        opcoes["Rotulo"].tolist(),
        default=opcoes["Rotulo"].head(5).tolist(),
        max_selections=12,
    )

    df_comp = opcoes[opcoes["Rotulo"].isin(selecionadas)].copy()
    if df_comp.empty:
        st.info("Selecione ao menos uma oferta para comparar.")
    else:
        col_comp1, col_comp2 = st.columns(2)
        with col_comp1:
            fig_comp_volume = px.bar(
                df_comp.sort_values("Valor_Total_Registrado", ascending=True),
                x="Valor_Total_Registrado",
                y="Numero_Processo",
                color="Nome_Lider",
                orientation="h",
                hover_data=["Nome_Emissor", "Status_Requerimento", "Publico_alvo"],
                labels={
                    "Valor_Total_Registrado": "Volume registrado",
                    "Numero_Processo": "Processo CVM",
                },
            )
            st.plotly_chart(fig_comp_volume, use_container_width=True)

        with col_comp2:
            eixo_y_macro = (
                "Pontos_IFIX_Data_Oferta"
                if df_comp["Pontos_IFIX_Data_Oferta"].notna().any()
                else "Valor_Total_Registrado"
            )
            fig_comp_macro = px.scatter(
                df_comp,
                x="Taxa_Selic_Data_Oferta",
                y=eixo_y_macro,
                size="Valor_Total_Registrado",
                color="Status_Requerimento",
                hover_data=["Numero_Processo", "Nome_Emissor", "Nome_Lider"],
                labels={
                    "Taxa_Selic_Data_Oferta": "Selic (%)",
                    "Pontos_IFIX_Data_Oferta": "IFIX",
                    "Valor_Total_Registrado": "Volume registrado",
                },
            )
            st.plotly_chart(fig_comp_macro, use_container_width=True)

        colunas_comparacao = [
            "Numero_Processo",
            "Data_requerimento",
            "Nome_Emissor",
            "Nome_Lider",
            "Tipo_Oferta",
            "Valor_Total_Registrado",
            "Status_Requerimento",
            "Publico_alvo",
            "Taxa_Selic_Data_Oferta",
            "Pontos_IFIX_Data_Oferta",
        ] + [col for col in ["IPCA_12m_Data_Oferta", "CDI_Data_Oferta", "USD_BRL_Data_Oferta"] if col in df_comp.columns]
        st.dataframe(
            df_comp[colunas_comparacao].sort_values("Valor_Total_Registrado", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


with tab_lideres:
    st.subheader("Ranking e benchmarking de coordenadores lideres")

    ranking = (
        df_filtrado.groupby("Nome_Lider", as_index=False)
        .agg(
            Volume_Total=("Valor_Total_Registrado", "sum"),
            Quantidade_Ofertas=("Numero_Processo", "count"),
            Ticket_Medio=("Valor_Total_Registrado", "mean"),
            Selic_Media=("Taxa_Selic_Data_Oferta", "mean"),
            IFIX_Medio=("Pontos_IFIX_Data_Oferta", "mean"),
        )
        .sort_values("Volume_Total", ascending=False)
    )
    ranking["Market_Share"] = ranking["Volume_Total"] / ranking["Volume_Total"].sum()

    top_n = st.slider("Quantidade de coordenadores no ranking", 5, 30, 10)
    ranking_top = ranking.head(top_n)

    col_rank1, col_rank2 = st.columns(2)
    with col_rank1:
        fig_ranking = px.bar(
            ranking_top.sort_values("Volume_Total", ascending=True),
            x="Volume_Total",
            y="Nome_Lider",
            orientation="h",
            labels={"Volume_Total": "Volume total", "Nome_Lider": "Coordenador lider"},
            color_discrete_sequence=["#002F6C"],
        )
        st.plotly_chart(fig_ranking, use_container_width=True)

    with col_rank2:
        fig_share = px.bar(
            ranking_top,
            x="Nome_Lider",
            y="Market_Share",
            labels={"Nome_Lider": "Coordenador lider", "Market_Share": "Market share"},
            color="Quantidade_Ofertas",
            color_continuous_scale="Teal",
        )
        fig_share.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig_share, use_container_width=True)

    ranking_grid = ranking.assign(
        Market_Share_Texto=lambda df: df["Market_Share"].map(lambda x: f"{x:.2%}")
    )
    selecionadas_ranking = exibir_grade_interativa(ranking_grid, key="ranking_aggrid")
    if selecionadas_ranking:
        st.session_state["lider_drilldown"] = selecionadas_ranking[0]["Nome_Lider"]

    lider_drill = st.session_state.get("lider_drilldown")
    if lider_drill:
        st.markdown(f"#### Drill-down: {lider_drill}")
        df_drill = df_filtrado[df_filtrado["Nome_Lider"] == lider_drill]
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            fig_drill = px.bar(
                df_drill.groupby("Ano_Mes", as_index=False)["Valor_Total_Registrado"].sum(),
                x="Ano_Mes",
                y="Valor_Total_Registrado",
                labels={"Valor_Total_Registrado": "Volume"},
            )
            st.plotly_chart(fig_drill, use_container_width=True)
        with col_d2:
            fig_drill_status = px.pie(
                df_drill,
                names="Status_Requerimento",
                values="Valor_Total_Registrado",
                hole=0.45,
            )
            st.plotly_chart(fig_drill_status, use_container_width=True)

    fig_treemap = px.treemap(
        df_filtrado,
        path=["Nome_Lider", "Nome_Emissor"],
        values="Valor_Total_Registrado",
        color="Taxa_Selic_Data_Oferta",
        color_continuous_scale="RdYlGn_r",
        title="Distribuicao de volume por coordenador e emissor",
    )
    st.plotly_chart(fig_treemap, use_container_width=True)


with tab_base:
    st.subheader("Base real processada")
    st.caption(f"Fonte carregada: {PROCESSED_DATA_PATH.relative_to(PROJECT_ROOT)}")

    colunas_exibir = [
        "Numero_Processo",
        "Data_requerimento",
        "Nome_Emissor",
        "Nome_Lider",
        "Tipo_Oferta",
        "Valor_Total_Registrado",
        "Status_Requerimento",
        "Publico_alvo",
        "Taxa_Selic_Data_Oferta",
        "Pontos_IFIX_Data_Oferta",
    ] + [col for col in ["IPCA_12m_Data_Oferta", "CDI_Data_Oferta", "USD_BRL_Data_Oferta"] if col in df_filtrado.columns]

    selecionadas_base = exibir_grade_interativa(df_filtrado[colunas_exibir], key="base_aggrid")
    if selecionadas_base:
        st.markdown("#### Oferta selecionada")
        st.json(selecionadas_base[0])

    csv_export = df_filtrado[colunas_exibir].to_csv(sep=";", index=False).encode("utf-8")
    st.download_button(
        "Baixar recorte filtrado",
        data=csv_export,
        file_name="ofertas_fiis_filtradas.csv",
        mime="text/csv",
    )


with tab_copiloto:
    st.subheader("Assistente de research")
    st.caption(
        "O agente usa memoria de conversa, a base processada e tools para macro atual, consulta CVM e spread contra CDI."
    )

    if "mensagens" not in st.session_state:
        st.session_state.mensagens = []

    for msg in st.session_state.mensagens:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pergunta = st.chat_input(
        "Pergunte sobre ranking, volume, coordenadores, publico-alvo, Selic, CDI, IPCA ou IFIX..."
    )

    if pergunta:
        st.session_state.mensagens.append({"role": "user", "content": pergunta})
        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            with st.spinner("Analisando a base de ofertas de FIIs..."):
                try:
                    resposta = carregar_agente().invoke({"input": pergunta})
                    texto_resposta = resposta.get("output", str(resposta))
                    st.markdown(texto_resposta)
                    st.session_state.mensagens.append(
                        {"role": "assistant", "content": texto_resposta}
                    )
                except Exception as e:
                    st.error(f"Nao foi possivel executar o agente de IA: {e}")
