from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from database.build_common import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    _coalesce_duplicate_columns,
    _ensure_columns,
    _normalizar_yield_mensal,
    _read_csv,
    _to_datetime,
    _to_numeric,
)
from data_processing.confidence_scorer import enriquecer_dataframe_com_confianca


def _classificar_preco_b3(row: pd.Series) -> str:
    if pd.isna(row.get("preco_emissao")) or pd.isna(row.get("preco_cota_b3")):
        return "Sem comparavel B3"
    if row["preco_emissao"] < row["preco_cota_b3"] * 0.98:
        return "Emissao abaixo da B3"
    if row["preco_emissao"] > row["preco_cota_b3"] * 1.02:
        return "Emissao acima da B3"
    return "Preco alinhado a B3"


def _classificar_preco_vp(row: pd.Series) -> str:
    if pd.isna(row.get("preco_emissao")) or pd.isna(row.get("valor_cota_vpc")):
        return "Sem VP/C"
    if row["preco_emissao"] < row["valor_cota_vpc"] * 0.98:
        return "Desconto sobre VP"
    if row["preco_emissao"] > row["valor_cota_vpc"] * 1.02:
        return "Premio sobre VP"
    return "Proximo ao VP"


def _classificar_liquidez(row: pd.Series) -> str:
    volume = row.get("volume_medio_diario")
    oferta = row.get("valor_total_registrado")
    if pd.isna(volume):
        return "Sem liquidez mapeada"
    if pd.notna(oferta) and oferta > 0:
        ratio = volume / oferta
        if ratio >= 0.01:
            return "Liquidez forte para o tamanho da oferta"
        if ratio >= 0.002:
            return "Liquidez intermediaria"
    if volume >= 1_000_000:
        return "Liquidez absoluta alta"
    if volume >= 100_000:
        return "Liquidez absoluta moderada"
    return "Liquidez baixa"


def _classificar_historico(row: pd.Series) -> str:
    total = row.get("total_emissoes")
    if pd.isna(total):
        return "Sem historico de emissoes"
    if total >= 5:
        return "Emissor recorrente"
    if total >= 2:
        return "Historico moderado"
    return "Primeira emissao mapeada"


def _score_oferta(row: pd.Series) -> float:
    score = 0.0
    if row.get("sinal_preco_b3") == "Emissao abaixo da B3":
        score += 30
    elif row.get("sinal_preco_b3") == "Preco alinhado a B3":
        score += 15
    elif row.get("sinal_preco_b3") == "Emissao acima da B3":
        score -= 15

    if row.get("sinal_preco_vp") == "Desconto sobre VP":
        score += 25
    elif row.get("sinal_preco_vp") == "Proximo ao VP":
        score += 10
    elif row.get("sinal_preco_vp") == "Premio sobre VP":
        score -= 10

    liquidez = row.get("sinal_liquidez")
    if liquidez in {"Liquidez forte para o tamanho da oferta", "Liquidez absoluta alta"}:
        score += 20
    elif liquidez in {"Liquidez intermediaria", "Liquidez absoluta moderada"}:
        score += 10

    historico = row.get("sinal_historico")
    if historico == "Emissor recorrente":
        score += 10
    elif historico == "Historico moderado":
        score += 5

    if pd.notna(row.get("valor_total_registrado")) and row["valor_total_registrado"] >= 100_000_000:
        score += 10
    if pd.notna(row.get("taxa_selic_data_oferta")) and row["taxa_selic_data_oferta"] <= 10:
        score += 5

    dy = row.get("dy_projetado_oferta")
    if pd.notna(dy):
        if dy >= 0.13:
            score += 15
        elif dy >= 0.10:
            score += 10
        elif dy >= 0.08:
            score += 5
        elif dy < 0.06:
            score -= 10

    return max(0.0, min(100.0, score))


def _leitura_priorizacao(score: float) -> str:
    if pd.isna(score):
        return "Sem score"
    if score >= 70:
        return "Prioridade alta para analise"
    if score >= 45:
        return "Prioridade media"
    if score >= 20:
        return "Prioridade baixa"
    return "Monitorar apenas"


def _build_oferta_inteligencia(
    ofertas: pd.DataFrame,
    metricas: pd.DataFrame,
    oferta_projecoes: pd.DataFrame,
) -> pd.DataFrame:
    if ofertas.empty:
        return pd.DataFrame()

    base = ofertas.copy()
    if not metricas.empty:
        metricas_join = metricas.rename(
            columns={
                "cnpj": "cnpj_emissor",
                "preco_cota": "preco_cota_b3",
            }
        )
        cols_metricas = [
            "cnpj_emissor",
            "ticker",
            "patrimonio_liquido",
            "valor_cota_vpc",
            "preco_cota_b3",
            "p_vp",
            "numero_cotistas",
            "dividend_yield_mes",
            "taxa_administracao",
            "caixa_sobre_pl",
            "imoveis_sobre_pl",
            "cri_sobre_pl",
            "fii_sobre_pl",
            "passivo_sobre_pl",
            "volume_medio_diario",
            "total_emissoes",
            "volume_total_ofertas",
            "coordenador_principal",
        ]
        metricas_join = _ensure_columns(metricas_join, cols_metricas)
        base = base.merge(metricas_join, on="cnpj_emissor", how="left")
    else:
        for column in [
            "ticker",
            "patrimonio_liquido",
            "valor_cota_vpc",
            "preco_cota_b3",
            "p_vp",
            "numero_cotistas",
            "dividend_yield_mes",
            "taxa_administracao",
            "caixa_sobre_pl",
            "imoveis_sobre_pl",
            "cri_sobre_pl",
            "fii_sobre_pl",
            "passivo_sobre_pl",
            "volume_medio_diario",
            "total_emissoes",
            "volume_total_ofertas",
            "coordenador_principal",
        ]:
            base[column] = pd.NA

    if not oferta_projecoes.empty:
        proj_cols = [
            "numero_processo",
            "rendimento_12m_historico_por_cota",
            "meses_historico_utilizados",
            "dy_12m_historico_sobre_emissao",
            "dy_projetado_oferta",
            "confianca_extracao",
        ]
        proj = _ensure_columns(oferta_projecoes, proj_cols).rename(
            columns={"confianca_extracao": "confianca_dy_projetado"}
        )
        base = base.merge(proj, on="numero_processo", how="left")
    else:
        for column in [
            "rendimento_12m_historico_por_cota",
            "meses_historico_utilizados",
            "dy_12m_historico_sobre_emissao",
            "dy_projetado_oferta",
            "confianca_dy_projetado",
        ]:
            base[column] = pd.NA

    base["desconto_vs_b3"] = base["preco_emissao"] / base["preco_cota_b3"] - 1
    base["desconto_vs_vp"] = base["preco_emissao"] / base["valor_cota_vpc"] - 1
    base["p_vp_emissao"] = base["preco_emissao"] / base["valor_cota_vpc"]
    base["liquidez_sobre_oferta"] = base["volume_medio_diario"] / base["valor_total_registrado"]

    base["sinal_preco_b3"] = base.apply(_classificar_preco_b3, axis=1)
    base["sinal_preco_vp"] = base.apply(_classificar_preco_vp, axis=1)
    base["sinal_liquidez"] = base.apply(_classificar_liquidez, axis=1)
    base["sinal_historico"] = base.apply(_classificar_historico, axis=1)
    base["score_priorizacao"] = base.apply(_score_oferta, axis=1)
    base["leitura_priorizacao"] = base["score_priorizacao"].map(_leitura_priorizacao)

    critical = [
        "preco_emissao",
        "dy_12m_historico_sobre_emissao",
        "dy_projetado_oferta",
        "preco_cota_b3",
        "valor_cota_vpc",
        "p_vp",
        "volume_medio_diario",
        "taxa_selic_data_oferta",
        "cdi_data_oferta",
        "valor_total_registrado",
        "nome_lider",
        "destinacao_recursos",
        "regime_distribuicao",
        "administrador",
    ]
    base = _ensure_columns(base, list(dict.fromkeys([*base.columns.tolist(), *critical])))
    base["campos_criticos_total"] = len(critical)
    base["campos_criticos_preenchidos"] = base[critical].notna().sum(axis=1)
    base["cobertura_analise_percentual"] = (
        base["campos_criticos_preenchidos"] / base["campos_criticos_total"] * 100
    ).round(2)
    base["atualizado_em"] = datetime.now()
    base = enriquecer_dataframe_com_confianca(base)

    columns = [
        "numero_processo",
        "numero_requerimento",
        "rito_requerimento",
        "cnpj_emissor",
        "ticker",
        "nome_emissor",
        "cnpj_lider",
        "nome_lider",
        "grupo_coordenador",
        "data_requerimento",
        "data_registro",
        "data_encerramento",
        "status_requerimento",
        "tipo_requerimento",
        "tipo_oferta",
        "publico_alvo",
        "bookbuilding",
        "tem_bookbuilding",
        "oferta_inicial",
        "destinacao_recursos",
        "mercado_negociacao",
        "regime_distribuicao",
        "administrador",
        "gestor",
        "quantidade_registrada",
        "valor_total_registrado",
        "preco_emissao",
        "dias_ate_registro",
        "dias_ate_encerramento",
        "oferta_encerrada",
        "num_investidores_mapeados",
        "quantidade_vm_investidores_mapeados",
        "participacao_pessoa_natural",
        "preco_cota_b3",
        "valor_cota_vpc",
        "p_vp",
        "patrimonio_liquido",
        "numero_cotistas",
        "dividend_yield_mes",
        "rendimento_12m_historico_por_cota",
        "meses_historico_utilizados",
        "dy_12m_historico_sobre_emissao",
        "dy_projetado_oferta",
        "confianca_dy_projetado",
        "taxa_administracao",
        "caixa_sobre_pl",
        "imoveis_sobre_pl",
        "cri_sobre_pl",
        "fii_sobre_pl",
        "passivo_sobre_pl",
        "volume_medio_diario",
        "total_emissoes",
        "volume_total_ofertas",
        "coordenador_principal",
        "desconto_vs_b3",
        "desconto_vs_vp",
        "p_vp_emissao",
        "liquidez_sobre_oferta",
        "taxa_selic_data_oferta",
        "cdi_data_oferta",
        "ipca_12m_data_oferta",
        "usd_brl_data_oferta",
        "pontos_ifix_data_oferta",
        "sinal_preco_b3",
        "sinal_preco_vp",
        "sinal_liquidez",
        "sinal_historico",
        "score_priorizacao",
        "leitura_priorizacao",
        "campos_criticos_preenchidos",
        "campos_criticos_total",
        "cobertura_analise_percentual",
        "confianca_total",
        "confianca_nivel",
        "confianca_dados",
        "confianca_sinais",
        "confianca_contexto",
        "confianca_resumo",
        "dados_ausentes_criticos",
        "atualizado_em",
    ]
    return _ensure_columns(base, columns).drop_duplicates("numero_processo", keep="last")


