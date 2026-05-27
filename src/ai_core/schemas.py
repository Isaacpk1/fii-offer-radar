from __future__ import annotations

from pydantic import BaseModel, Field


class OfertaPriorizada(BaseModel):
    numero_processo: str
    ticker: str | None = None
    nome_emissor: str
    preco_emissao: float | None = None
    p_vp_emissao: float | None = None
    desconto_vs_b3: float | None = None
    score_priorizacao: float | None = None
    leitura_priorizacao: str | None = None
    cobertura_analise_percentual: float | None = None
    diagnostico: str = Field(description="2 frases: ponto forte e principal risco da oferta")


class RankingOfertas(BaseModel):
    ofertas: list[OfertaPriorizada]
    contexto_macro: str = Field(description="Selic e CDI atual e impacto no lote")
    proxima_acao: str = Field(description="O que o analista deve fazer primeiro")
