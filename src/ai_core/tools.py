from __future__ import annotations

from ai_core.macro import obter_macro_atual
from ai_core.schemas import OfertaPriorizada, RankingOfertas
from ai_core.tools_confidence import avaliar_confianca_analise
from ai_core.tools_ranking import rankear_com_diagnostico, rankear_ofertas_prioritarias
from ai_core.tools_read import (
    buscar_macro_atual,
    buscar_noticias_contexto,
    calcular_spread_cdi,
    consultar_oferta_cvm,
    consultar_tese_oferta,
    resumir_mercado_ofertas,
    resumir_qualidade_base,
)
from ai_core.tools_write import gerar_brief_oferta, registrar_decisao_analista
from ai_core.warehouse import (
    _carregar_base_csv,
    _limite,
    _normalizar_df,
    _query_warehouse,
    _to_json,
    _tokens_busca,
    _warehouse_disponivel,
)

AGENT_TOOLS = [
    avaliar_confianca_analise,
    buscar_macro_atual,
    consultar_tese_oferta,
    buscar_noticias_contexto,
    rankear_ofertas_prioritarias,
    rankear_com_diagnostico,
    resumir_qualidade_base,
    resumir_mercado_ofertas,
    consultar_oferta_cvm,
    calcular_spread_cdi,
    gerar_brief_oferta,
    registrar_decisao_analista,
]

__all__ = [
    "AGENT_TOOLS",
    "OfertaPriorizada",
    "RankingOfertas",
    "avaliar_confianca_analise",
    "buscar_macro_atual",
    "buscar_noticias_contexto",
    "calcular_spread_cdi",
    "consultar_oferta_cvm",
    "consultar_tese_oferta",
    "gerar_brief_oferta",
    "obter_macro_atual",
    "rankear_com_diagnostico",
    "rankear_ofertas_prioritarias",
    "registrar_decisao_analista",
    "resumir_mercado_ofertas",
    "resumir_qualidade_base",
]
