import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.components import tabela_interativa
from frontend.config import BRAND_BLUE, TEAL


def _rotulo_fii(row: pd.Series) -> str:
    ticker = str(row.get("ticker") or "").strip()
    cnpj = str(row.get("cnpj") or "").strip()
    nome = str(row.get("nome_emissor") or row.get("coordenador_principal") or "").strip()

    if ticker and ticker.lower() != "nan":
        return f"{ticker} | {cnpj}" if cnpj else ticker
    if nome and nome.lower() != "nan":
        return f"Sem B3 | {nome[:55]} | {cnpj}" if cnpj else f"Sem B3 | {nome[:55]}"
    return f"Sem B3 | {cnpj}" if cnpj else "Sem identificador"


def render_fii_compare(metricas: pd.DataFrame) -> None:
    st.subheader("Suporte do fundo")
    st.markdown(
        (
            '<div class="section-note">Esta aba apoia a leitura do fundo por trás da oferta. '
            'Preço, P/VP de mercado e liquidez aparecem apenas quando o ticker foi mapeado e a coleta B3 funcionou; '
            'fundos sem B3 ainda podem ter VP/C, patrimônio, cotistas, rendimentos e histórico de ofertas úteis para análise.</div>'
        ),
        unsafe_allow_html=True,
    )
    if metricas.empty:
        st.warning("Base de metricas nao encontrada. Rode `python src/main.py`.")
        return

    with_data = metricas.copy()
    with_data["rotulo_fii"] = with_data.apply(_rotulo_fii, axis=1)
    opcoes = with_data["rotulo_fii"].dropna().astype(str).sort_values().unique().tolist()

    total = len(with_data)
    com_b3 = int(with_data["preco_cota"].notna().sum()) if "preco_cota" in with_data else 0
    sem_b3_com_vpc = (
        int((with_data["preco_cota"].isna() & with_data["valor_cota_vpc"].notna()).sum())
        if {"preco_cota", "valor_cota_vpc"}.issubset(with_data.columns)
        else 0
    )
    com_historico = int(with_data["total_emissoes"].fillna(0).gt(0).sum()) if "total_emissoes" in with_data else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fundos na base", total)
    c2.metric("Com B3 coletado", com_b3)
    c3.metric("Sem B3, com VP/C", sem_b3_com_vpc)
    c4.metric("Com historico de oferta", com_historico)

    st.caption(
        "A ausência de B3 significa ausência de ticker/preço/liquidez coletados, não ausência de dados do fundo. "
        "Use VP/C, patrimônio, cotistas e histórico como suporte quando o comparável de mercado não existir."
    )

    selecionados = st.multiselect("Selecione ate 6 fundos", opcoes, default=opcoes[:6], max_selections=6)
    if not selecionados:
        st.info("Selecione ao menos um fundo para abrir a comparacao.")
        return

    df_sel = with_data[with_data["rotulo_fii"].astype(str).isin(selecionados)].copy()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fundos selecionados", len(df_sel))
    c2.metric("Com preco B3", int(df_sel["preco_cota"].notna().sum()) if "preco_cota" in df_sel else 0)
    c3.metric("Com preco emissao", int(df_sel["preco_emissao"].notna().sum()) if "preco_emissao" in df_sel else 0)
    c4.metric("Com P/VP mercado", int(df_sel["p_vp"].notna().sum()) if "p_vp" in df_sel else 0)

    col_price, col_liq = st.columns(2)
    with col_price:
        price_df = df_sel[
            [c for c in ["rotulo_fii", "preco_cota", "preco_emissao"] if c in df_sel.columns]
        ].melt(
            id_vars="rotulo_fii",
            value_vars=[c for c in ["preco_cota", "preco_emissao"] if c in df_sel.columns],
            var_name="metrica",
            value_name="valor",
        ).dropna(subset=["valor"])
        if not price_df.empty:
            fig = px.bar(
                price_df,
                x="rotulo_fii",
                y="valor",
                color="metrica",
                barmode="group",
                title="Preco B3 vs preco de emissao",
                labels={"valor": "Preco", "rotulo_fii": "Fundo"},
                color_discrete_map={"preco_cota": BRAND_BLUE, "preco_emissao": TEAL},
            )
            fig.update_layout(height=390, margin={"l": 10, "r": 10, "t": 48, "b": 20})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Os fundos selecionados nao tem preco B3 ou preco de emissao coletado.")
    with col_liq:
        if "volume_medio_diario" in df_sel.columns and df_sel["volume_medio_diario"].notna().any():
            fig = px.bar(
                df_sel.dropna(subset=["volume_medio_diario"]).sort_values("volume_medio_diario"),
                x="volume_medio_diario",
                y="rotulo_fii",
                orientation="h",
                title="Liquidez media diaria",
                color_discrete_sequence=[BRAND_BLUE],
                labels={"volume_medio_diario": "Volume medio", "rotulo_fii": "Fundo"},
            )
            fig.update_layout(height=390, margin={"l": 10, "r": 10, "t": 48, "b": 20})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Liquidez B3 sem cobertura para os selecionados.")

    table_cols = ["rotulo_fii", "ticker", "cnpj", "patrimonio_liquido", "valor_cota_vpc", "preco_cota", "p_vp", "preco_emissao", "desconto_oferta_vp", "desconto_oferta_b3", "volume_medio_diario", "total_emissoes", "volume_total_ofertas", "coordenador_principal", "numero_cotistas", "dividend_yield_12m", "status_viabilidade_oferta"]
    st.markdown("#### Tabela comparativa")
    tabela_interativa(df_sel[[c for c in table_cols if c in df_sel.columns]], "fii_compare")


