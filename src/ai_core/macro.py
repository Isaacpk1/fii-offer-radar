from __future__ import annotations

from bcb import sgs

from ai_core.tool_config import MACRO_CODES


def obter_macro_atual(indicador: str) -> float:
    chave = indicador.strip().lower()
    if chave not in MACRO_CODES:
        raise ValueError(f"Indicador nao suportado: {indicador}")

    serie = sgs.get({chave: MACRO_CODES[chave]})
    return float(serie.iloc[-1, 0])
