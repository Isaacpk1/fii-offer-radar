from pathlib import Path
import sys

import streamlit as st

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from frontend.components import apply_filters, render_header, render_sidebar_status
from frontend.data import load_metricas, load_oferta_inteligencia, load_ofertas, load_quality
from frontend.styles import configure_page, inject_css
from frontend.views import (
    render_copilot,
    render_fii_compare,
    render_market,
    render_offer_compare,
    render_offer_intelligence,
    render_quality,
    render_warehouse_explorer,
)


def main() -> None:
    configure_page()
    inject_css()
    render_header()

    ofertas_base = load_ofertas()
    metricas = load_metricas()
    oferta_inteligencia = load_oferta_inteligencia()
    quality = load_quality()

    render_sidebar_status()
    ofertas_filtradas = apply_filters(ofertas_base)

    if ofertas_base.empty:
        st.warning("Nenhuma base de ofertas foi encontrada. Rode `python src/main.py` antes de abrir o app.")
        st.stop()
    if ofertas_filtradas.empty:
        st.warning("Nenhuma oferta encontrada para os filtros selecionados.")
        st.stop()

    if not oferta_inteligencia.empty and "numero_processo" in oferta_inteligencia.columns:
        processos_filtrados = set(ofertas_filtradas["numero_processo"].astype(str))
        oferta_inteligencia_filtrada = oferta_inteligencia[
            oferta_inteligencia["numero_processo"].astype(str).isin(processos_filtrados)
        ].copy()
    else:
        oferta_inteligencia_filtrada = oferta_inteligencia

    tab_tese, tab_mercado, tab_ofertas, tab_fiis, tab_qualidade, tab_warehouse, tab_copiloto = st.tabs(
        [
            "Tese da Oferta",
            "Mercado",
            "Ofertas",
            "Suporte FII",
            "Qualidade",
            "Tabelas",
            "Copiloto",
        ]
    )

    with tab_tese:
        render_offer_intelligence(oferta_inteligencia_filtrada)
    with tab_mercado:
        render_market(ofertas_filtradas)
    with tab_ofertas:
        render_offer_compare(ofertas_filtradas)
    with tab_fiis:
        render_fii_compare(metricas)
    with tab_qualidade:
        render_quality(quality)
    with tab_warehouse:
        render_warehouse_explorer()
    with tab_copiloto:
        render_copilot(ofertas_filtradas)


if __name__ == "__main__":
    main()
