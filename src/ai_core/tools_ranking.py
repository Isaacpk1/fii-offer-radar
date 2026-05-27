from __future__ import annotations

import json

from langchain.tools import tool

from ai_core.schemas import RankingOfertas
from ai_core.tool_config import CORE_COLUMNS
from ai_core.tools_read import buscar_macro_atual
from ai_core.warehouse import _limite, _query_warehouse, _to_json


@tool
def rankear_ofertas_prioritarias(limite: str = "10") -> str:
    """Lista ofertas com maior score de priorizacao, trazendo preco, P/VP, descontos, liquidez e cobertura."""
    try:
        n = _limite(limite, default=10, maximum=30)
        cols = ", ".join(CORE_COLUMNS)
        df = _query_warehouse(
            f"""
            SELECT {cols}
            FROM oferta_inteligencia
            ORDER BY score_priorizacao DESC NULLS LAST,
                     cobertura_analise_percentual DESC NULLS LAST,
                     valor_total_registrado DESC NULLS LAST
            LIMIT ?
            """,
            [n],
        )
        if df.empty:
            return "Nao ha ofertas em oferta_inteligencia para rankear."
        return _to_json(df)
    except Exception as e:
        return f"Erro ao rankear ofertas prioritarias: {e}"
@tool
def rankear_com_diagnostico(limite: str = "5") -> str:
    """
    Retorna um prompt com ranking priorizado para o LLM transformar em JSON RankingOfertas.
    Sempre instrui o LLM a responder apenas JSON valido no schema RankingOfertas.
    """
    try:
        n = _limite(limite, default=5, maximum=15)
        cols = [
            "numero_processo",
            "ticker",
            "nome_emissor",
            "preco_emissao",
            "p_vp_emissao",
            "desconto_vs_b3",
            "score_priorizacao",
            "leitura_priorizacao",
            "cobertura_analise_percentual",
            "dy_projetado_oferta",
            "sinal_preco_b3",
            "sinal_preco_vp",
            "sinal_liquidez",
            "sinal_historico",
            "valor_total_registrado",
            "confianca_total",
            "confianca_nivel",
            "confianca_resumo",
            "dados_ausentes_criticos",
        ]
        df = _query_warehouse(
            f"""
            SELECT {", ".join(cols)}
            FROM oferta_inteligencia
            ORDER BY score_priorizacao DESC NULLS LAST,
                     cobertura_analise_percentual DESC NULLS LAST,
                     valor_total_registrado DESC NULLS LAST
            LIMIT ?
            """,
            [n],
        )
        if df.empty:
            return json.dumps(
                {
                    "ofertas": [],
                    "contexto_macro": "Nao ha ofertas em oferta_inteligencia para rankear.",
                    "proxima_acao": "Gerar ou atualizar o warehouse antes da triagem.",
                },
                ensure_ascii=False,
            )

        selic = buscar_macro_atual.invoke("selic")
        cdi = buscar_macro_atual.invoke("cdi")
        schema = RankingOfertas.model_json_schema()
        return (
            "Retorne APENAS um JSON valido, sem markdown, no schema RankingOfertas. "
            "Nao invente campos fora do schema. "
            "Cada diagnostico deve ter exatamente 2 frases: uma sobre ponto forte e outra sobre principal risco. "
            f"Schema: {json.dumps(schema, ensure_ascii=False)}\n"
            f"Contexto macro atual: {selic}; {cdi}.\n"
            f"Dados das ofertas: {_to_json(df)}"
        )
    except Exception as e:
        return f"Erro ao montar ranking com diagnostico: {e}"
