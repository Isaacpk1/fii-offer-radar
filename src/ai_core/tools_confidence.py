from __future__ import annotations

import json

from langchain.tools import tool

from ai_core.warehouse import _query_warehouse
from data_processing.confidence_scorer import calcular_confianca


@tool
def avaliar_confianca_analise(numero_processo: str) -> str:
    """
    Avalia e retorna o breakdown de confianca da analise de uma oferta.
    Use sempre antes de emitir conclusao sobre uma oferta especifica.
    """
    try:
        df = _query_warehouse(
            """
            SELECT *
            FROM oferta_inteligencia
            WHERE UPPER(CAST(numero_processo AS VARCHAR)) = ?
            """,
            [numero_processo.strip().upper()],
        )
        if df.empty:
            return f"Processo {numero_processo} nao encontrado no warehouse."

        breakdown = calcular_confianca(df.iloc[0])
        return json.dumps(
            {
                "score_total": breakdown.score_total,
                "nivel": breakdown.nivel,
                "score_dados": breakdown.score_dados,
                "score_sinais": breakdown.score_sinais,
                "score_contexto": breakdown.score_contexto,
                "dados_ausentes": breakdown.dados_ausentes,
                "sinais_conflitantes": breakdown.sinais_conflitantes,
                "resumo": breakdown.resumo_auditavel,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return f"Erro ao calcular confianca: {e}"
