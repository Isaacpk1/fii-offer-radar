from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, Field


class ConfidenceBreakdown(BaseModel):
    """Breakdown auditavel da confianca por dimensao."""

    score_dados: float = Field(ge=0, le=40)
    dados_presentes: list[str]
    dados_ausentes: list[str]
    score_sinais: float = Field(ge=0, le=35)
    sinais_concordantes: list[str]
    sinais_conflitantes: list[str]
    score_contexto: float = Field(ge=0, le=25)
    contexto_obs: list[str]
    score_total: float = Field(ge=0, le=100)
    nivel: str
    resumo_auditavel: str


CAMPOS_CRITICOS = {
    "preco_emissao": 12,
    "valor_cota_vpc": 10,
    "preco_cota_b3": 8,
    "volume_medio_diario": 6,
    "p_vp_emissao": 4,
}

SINAIS = ["sinal_preco_b3", "sinal_preco_vp", "sinal_liquidez", "sinal_historico"]

SINAIS_POSITIVOS = {
    "emissao abaixo da b3",
    "preco alinhado a b3",
    "desconto sobre vp",
    "proximo ao vp",
    "liquidez forte",
    "liquidez absoluta alta",
    "liquidez intermediaria",
    "liquidez absoluta moderada",
    "emissor recorrente",
    "historico moderado",
}

SINAIS_NEGATIVOS = {
    "emissao acima da b3",
    "premio sobre vp",
    "liquidez baixa",
    "sem historico",
    "primeira emissao",
}

SINAIS_AUSENTES = {
    "sem preco b3",
    "sem vp/c",
    "sem liquidez",
    "sem historico de emissoes",
}


def _score_dados(row: pd.Series) -> tuple[float, list[str], list[str]]:
    presentes, ausentes = [], []
    score = 0.0
    for campo, peso in CAMPOS_CRITICOS.items():
        valor = row.get(campo)
        if pd.notna(valor) and valor != 0:
            score += peso
            presentes.append(campo)
        else:
            ausentes.append(campo)
    return round(score, 1), presentes, ausentes


def _classificar_sinal(valor: object) -> str:
    texto = str(valor or "").lower().strip()
    if not texto or texto in {"nan", "none", "nao informado"}:
        return "ausente"
    if any(fragmento in texto for fragmento in SINAIS_AUSENTES):
        return "ausente"
    if any(fragmento in texto for fragmento in SINAIS_POSITIVOS):
        return "positivo"
    if any(fragmento in texto for fragmento in SINAIS_NEGATIVOS):
        return "negativo"
    return "ausente"


def _score_sinais(row: pd.Series) -> tuple[float, list[str], list[str]]:
    positivos, negativos, ausentes = [], [], []

    for sinal in SINAIS:
        classe = _classificar_sinal(row.get(sinal))
        if classe == "positivo":
            positivos.append(sinal)
        elif classe == "negativo":
            negativos.append(sinal)
        else:
            ausentes.append(sinal)

    total_reconhecidos = len(positivos) + len(negativos)
    if total_reconhecidos == 0:
        return 0.0, [], SINAIS.copy()

    maioria = max(len(positivos), len(negativos))
    concordancia = maioria / total_reconhecidos
    penalidade_ausentes = len(ausentes) * 2.5
    score = max(0.0, round(35 * concordancia - penalidade_ausentes, 1))

    concordantes = positivos if len(positivos) >= len(negativos) else negativos
    conflitantes = negativos if len(positivos) >= len(negativos) else positivos
    return score, concordantes, conflitantes + ausentes


def _score_contexto(row: pd.Series) -> tuple[float, list[str]]:
    score = 0.0
    obs = []

    total_emissoes = row.get("total_emissoes")
    if pd.notna(total_emissoes) and total_emissoes > 0:
        pontos = min(10.0, float(total_emissoes) * 2)
        score += pontos
        obs.append(f"{int(total_emissoes)} emissao(oes) anteriores (+{pontos:.0f}pts)")
    else:
        obs.append("Sem historico de emissoes")

    volume = row.get("volume_medio_diario")
    if pd.notna(volume) and volume > 0:
        if volume >= 1_000_000:
            score += 10
            obs.append(f"Liquidez alta: R$ {volume / 1_000_000:.1f}M/dia (+10pts)")
        elif volume >= 200_000:
            score += 5
            obs.append(f"Liquidez moderada: R$ {volume / 1_000:.0f}k/dia (+5pts)")
        else:
            obs.append(f"Liquidez baixa: R$ {volume / 1_000:.0f}k/dia (0pts)")
    else:
        obs.append("Liquidez ausente (0pts)")

    if pd.notna(row.get("taxa_selic_data_oferta")):
        score += 5
        obs.append("Macro na data disponivel (+5pts)")
    else:
        obs.append("Macro na data ausente (0pts)")

    return round(score, 1), obs


def calcular_confianca(row: pd.Series) -> ConfidenceBreakdown:
    score_dados, presentes, ausentes = _score_dados(row)
    score_sinais, concordantes, conflitantes = _score_sinais(row)
    score_contexto, obs_contexto = _score_contexto(row)
    total = round(score_dados + score_sinais + score_contexto, 1)

    if total >= 80:
        nivel = "Alta"
    elif total >= 55:
        nivel = "Media"
    elif total >= 30:
        nivel = "Baixa"
    else:
        nivel = "Insuficiente"

    partes = []
    if ausentes:
        partes.append(f"dados ausentes: {', '.join(ausentes)}")
    if conflitantes:
        partes.append(f"sinais conflitantes: {', '.join(conflitantes)}")
    if not partes:
        partes.append("todos os dados criticos presentes e sinais concordantes")

    resumo = f"Confianca {nivel} ({total:.0f}/100): {'; '.join(partes)}."

    return ConfidenceBreakdown(
        score_dados=score_dados,
        dados_presentes=presentes,
        dados_ausentes=ausentes,
        score_sinais=score_sinais,
        sinais_concordantes=concordantes,
        sinais_conflitantes=conflitantes,
        score_contexto=score_contexto,
        contexto_obs=obs_contexto,
        score_total=total,
        nivel=nivel,
        resumo_auditavel=resumo,
    )


def enriquecer_dataframe_com_confianca(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona colunas auditaveis de confianca ao DataFrame de ofertas."""
    if df.empty:
        return df

    enriched = df.copy()
    breakdowns = enriched.apply(calcular_confianca, axis=1)
    enriched["confianca_total"] = breakdowns.apply(lambda item: item.score_total)
    enriched["confianca_nivel"] = breakdowns.apply(lambda item: item.nivel)
    enriched["confianca_dados"] = breakdowns.apply(lambda item: item.score_dados)
    enriched["confianca_sinais"] = breakdowns.apply(lambda item: item.score_sinais)
    enriched["confianca_contexto"] = breakdowns.apply(lambda item: item.score_contexto)
    enriched["confianca_resumo"] = breakdowns.apply(lambda item: item.resumo_auditavel)
    enriched["dados_ausentes_criticos"] = breakdowns.apply(lambda item: ", ".join(item.dados_ausentes))
    return enriched
