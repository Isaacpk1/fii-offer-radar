import pandas as pd
import streamlit as st

from frontend.config import STATUS_ALERTS_PATH, WAREHOUSE_PATH
from frontend.data import get_connection

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
except ImportError:
    AgGrid = None
    GridOptionsBuilder = None
    GridUpdateMode = None


def badge(text: str, kind: str = "") -> None:
    st.markdown(f'<span class="status-pill {kind}">{text}</span>', unsafe_allow_html=True)


def tabela_interativa(df: pd.DataFrame, key: str, height: int = 420) -> list[dict]:
    if df.empty:
        st.info("Tabela vazia ou fonte ainda nao carregada.")
        return []

    display_df = df.copy()
    for col in display_df.select_dtypes(include=["datetime64"]).columns:
        display_df[col] = display_df[col].dt.strftime("%Y-%m-%d")

    if AgGrid is None:
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=height)
        return []

    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(filter=True, sortable=True, resizable=True)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    response = AgGrid(
        display_df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=height,
        fit_columns_on_grid_load=False,
        use_container_width=True,
        key=key,
    )
    selected = response.get("selected_rows", [])
    if isinstance(selected, pd.DataFrame):
        return selected.to_dict("records")
    return selected or []


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    with st.sidebar:
        st.markdown("### Filtros")
        data_min = df["data_requerimento"].min().date()
        data_max = df["data_requerimento"].max().date()
        periodo = st.date_input("Periodo", value=(data_min, data_max), min_value=data_min, max_value=data_max)

        lideres = sorted(df["nome_lider"].dropna().unique()) if "nome_lider" in df else []
        status = sorted(df["status_requerimento"].dropna().unique()) if "status_requerimento" in df else []
        publicos = sorted(df["publico_alvo"].dropna().unique()) if "publico_alvo" in df else []

        lideres_sel = st.multiselect("Coordenador", lideres)
        status_sel = st.multiselect("Status", status)
        publicos_sel = st.multiselect("Publico-alvo", publicos)

    filtered = df.copy()
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio, fim = periodo
        filtered = filtered[
            (filtered["data_requerimento"].dt.date >= inicio)
            & (filtered["data_requerimento"].dt.date <= fim)
        ]
    if lideres_sel:
        filtered = filtered[filtered["nome_lider"].isin(lideres_sel)]
    if status_sel:
        filtered = filtered[filtered["status_requerimento"].isin(status_sel)]
    if publicos_sel:
        filtered = filtered[filtered["publico_alvo"].isin(publicos_sel)]
    return filtered


def render_header() -> None:
    source = "DuckDB" if get_connection() is not None else "CSV"
    st.markdown(
        f"""
        <div class="top-band">
            <p class="top-title">Primary FII Offers Intelligence | BTG Pactual</p>
            <div class="top-subtitle">
                Mesa de decisao para ofertas primarias de FIIs: emissao versus B3, valor patrimonial,
                liquidez, historico, macro e DY projetado da oferta.
            </div>
            <div style="margin-top: 10px;">
                <span class="status-pill status-ok">Fonte ativa: {source}</span>
                <span class="status-pill">Triagem de ofertas</span>
                <span class="status-pill">Resolucao CVM 160</span>
                <span class="status-pill">DY projetado separado do historico</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_status() -> None:
    with st.sidebar:
        st.markdown("### Estado da base")
        if WAREHOUSE_PATH.exists():
            badge("Warehouse carregado", "status-ok")
        else:
            badge("Warehouse ausente", "status-empty")

        if STATUS_ALERTS_PATH.exists():
            alertas = pd.read_json(STATUS_ALERTS_PATH)
            if not alertas.empty:
                st.warning(f"{len(alertas)} mudanca(s) de status detectada(s).")
                with st.expander("Alertas"):
                    st.dataframe(alertas, use_container_width=True, hide_index=True)
