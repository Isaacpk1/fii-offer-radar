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


def _build_dim_fii(informe: pd.DataFrame, metricas: pd.DataFrame, ofertas: pd.DataFrame) -> pd.DataFrame:
    cnpjs = pd.Series(dtype="object")
    for df, column in [(informe, "cnpj"), (metricas, "cnpj"), (ofertas, "cnpj_emissor")]:
        if not df.empty and column in df.columns:
            cnpjs = pd.concat([cnpjs, df[column].dropna().astype(str)])

    dim = pd.DataFrame({"cnpj": cnpjs.drop_duplicates()})
    if dim.empty:
        return dim

    if not ofertas.empty:
        nomes = ofertas[["cnpj_emissor", "nome_emissor"]].dropna().drop_duplicates("cnpj_emissor")
        nomes = nomes.rename(columns={"cnpj_emissor": "cnpj", "nome_emissor": "nome"})
        dim = dim.merge(nomes, on="cnpj", how="left")
    else:
        dim["nome"] = pd.NA

    if not informe.empty:
        info_cols = [
            "cnpj",
            "competencia",
            "nome_fundo",
            "nome_administrador",
            "segmento_atuacao",
            "tipo_gestao",
            "codigo_isin",
            "publico_alvo_fundo",
            "mandato",
        ]
        info = _ensure_columns(informe, info_cols)
        info = info.sort_values("competencia").drop_duplicates("cnpj", keep="last")
        dim = dim.merge(info, on="cnpj", how="left")
        dim["nome"] = dim["nome"].fillna(dim["nome_fundo"])
    else:
        for column in [
            "nome_administrador",
            "segmento_atuacao",
            "tipo_gestao",
            "codigo_isin",
            "publico_alvo_fundo",
            "mandato",
        ]:
            dim[column] = pd.NA

    tickers = pd.DataFrame()
    if not metricas.empty and {"cnpj", "ticker"}.issubset(metricas.columns):
        tickers = metricas[["cnpj", "ticker"]].dropna().drop_duplicates("cnpj")
        dim = dim.merge(tickers, on="cnpj", how="left")
    else:
        dim["ticker"] = pd.NA

    dim["administrador"] = dim.get("nome_administrador", pd.Series(pd.NA, index=dim.index))
    dim["gestor"] = pd.NA
    dim["segmento"] = dim.get("segmento_atuacao", pd.Series(pd.NA, index=dim.index))
    dim["tipo_fii"] = dim.get("tipo_gestao", pd.Series(pd.NA, index=dim.index))
    dim["codigo_isin"] = dim.get("codigo_isin", pd.Series(pd.NA, index=dim.index))
    dim["publico_alvo"] = dim.get("publico_alvo_fundo", pd.Series(pd.NA, index=dim.index))
    dim["mandato"] = dim.get("mandato", pd.Series(pd.NA, index=dim.index))
    dim["fonte_principal"] = "CVM"
    dim["atualizado_em"] = datetime.now()
    return dim[
        [
            "cnpj",
            "ticker",
            "nome",
            "administrador",
            "gestor",
            "segmento",
            "tipo_fii",
            "codigo_isin",
            "publico_alvo",
            "mandato",
            "fonte_principal",
            "atualizado_em",
        ]
    ]


def _build_metricas(informe: pd.DataFrame, ofertas: pd.DataFrame) -> pd.DataFrame:
    if informe.empty:
        return pd.DataFrame()

    metricas = informe.sort_values("competencia").drop_duplicates("cnpj", keep="last").copy()
    dy_historico = _ensure_columns(informe, ["cnpj", "competencia", "dividend_yield_mes"]).copy()
    dy_historico["dividend_yield_mes"] = _normalizar_yield_mensal(dy_historico["dividend_yield_mes"])
    dy_historico = dy_historico.dropna(subset=["cnpj", "competencia"]).sort_values(["cnpj", "competencia"])
    dy_historico["dividend_yield_12m_historico"] = (
        dy_historico.groupby("cnpj")["dividend_yield_mes"]
        .rolling(12, min_periods=3)
        .sum()
        .reset_index(level=0, drop=True)
    )
    dy_historico = dy_historico.drop_duplicates("cnpj", keep="last")
    metricas = metricas.merge(
        dy_historico[["cnpj", "dividend_yield_12m_historico"]],
        on="cnpj",
        how="left",
    )
    mercado = _read_csv(RAW_DATA_DIR / "fii_mercado_bruto.csv")
    if not mercado.empty:
        mercado = _ensure_columns(mercado, ["CNPJ_Emissor", "Ticker", "Preco_Cota", "Volume_Medio_Diario"])
        mercado = _to_numeric(mercado, ["Preco_Cota", "Volume_Medio_Diario"])
        mercado = mercado.rename(
            columns={
                "CNPJ_Emissor": "cnpj",
                "Ticker": "ticker",
                "Preco_Cota": "preco_cota",
                "Volume_Medio_Diario": "volume_medio_diario",
            }
        ).drop_duplicates("cnpj", keep="last")
        metricas = metricas.merge(
            mercado[["cnpj", "ticker", "preco_cota", "volume_medio_diario"]],
            on="cnpj",
            how="left",
        )
    else:
        metricas["ticker"] = pd.NA
        metricas["preco_cota"] = pd.NA
        metricas["volume_medio_diario"] = pd.NA

    if not ofertas.empty:
        historico = (
            ofertas.groupby("cnpj_emissor", as_index=False)
            .agg(
                total_emissoes=("numero_processo", "count"),
                volume_total_ofertas=("valor_total_registrado", "sum"),
            )
            .rename(columns={"cnpj_emissor": "cnpj"})
        )
        recentes = (
            ofertas.sort_values("data_requerimento")
            .drop_duplicates("cnpj_emissor", keep="last")
            .rename(columns={"cnpj_emissor": "cnpj", "preco_emissao": "preco_emissao"})
        )
        if "nome_lider" in ofertas.columns:
            lideres = (
                ofertas.groupby(["cnpj_emissor", "nome_lider"], as_index=False)
                .agg(volume_lider=("valor_total_registrado", "sum"))
                .sort_values(["cnpj_emissor", "volume_lider"], ascending=[True, False])
                .drop_duplicates("cnpj_emissor")
                .rename(columns={"cnpj_emissor": "cnpj", "nome_lider": "coordenador_principal"})
            )
            historico = historico.merge(lideres[["cnpj", "coordenador_principal"]], on="cnpj", how="left")
        else:
            historico["coordenador_principal"] = pd.NA

        metricas = metricas.merge(
            recentes[["cnpj", "preco_emissao"]],
            on="cnpj",
            how="left",
        ).merge(historico, on="cnpj", how="left")
    else:
        for column in ["preco_emissao", "total_emissoes", "volume_total_ofertas", "coordenador_principal"]:
            metricas[column] = pd.NA

    columns = [
        "cnpj",
        "ticker",
        "competencia",
        "patrimonio_liquido",
        "valor_cota_vpc",
        "preco_cota",
        "p_vp",
        "p_vp_emissao",
        "preco_emissao",
        "desconto_oferta_vp",
        "volume_medio_diario",
        "total_emissoes",
        "volume_total_ofertas",
        "coordenador_principal",
        "numero_cotistas",
        "taxa_administracao",
        "taxa_custodiante",
        "dividend_yield_mes",
        "dividend_yield_12m_historico",
        "rentabilidade_patrimonial_mes",
        "caixa_sobre_pl",
        "imoveis_sobre_pl",
        "cri_sobre_pl",
        "fii_sobre_pl",
        "passivo_sobre_pl",
        "vacancia_fisica",
        "vacancia_financeira",
        "numero_imoveis",
        "status_viabilidade_oferta",
    ]
    metricas = _ensure_columns(metricas, columns)
    numeric_columns = [col for col in columns if col not in {"cnpj", "ticker", "competencia", "coordenador_principal", "status_viabilidade_oferta"}]
    metricas = _to_numeric(metricas, numeric_columns)
    metricas["dividend_yield_mes"] = _normalizar_yield_mensal(metricas["dividend_yield_mes"])
    metricas["p_vp"] = metricas["preco_cota"] / metricas["valor_cota_vpc"]
    metricas["desconto_oferta_b3"] = metricas["preco_emissao"] / metricas["preco_cota"] - 1
    metricas["p_vp_emissao"] = metricas["preco_emissao"] / metricas["valor_cota_vpc"]
    metricas["desconto_oferta_vp"] = metricas["p_vp_emissao"] - 1
    metricas["dividend_yield_12m"] = pd.NA
    condicoes = [
        metricas["preco_cota"].isna() | metricas["preco_emissao"].isna(),
        metricas["preco_emissao"] < metricas["preco_cota"],
        metricas["preco_emissao"] > metricas["preco_cota"],
    ]
    metricas["status_viabilidade_oferta"] = pd.Series(
        pd.NA,
        index=metricas.index,
        dtype="object",
    )
    metricas["status_viabilidade_oferta"] = metricas["status_viabilidade_oferta"].mask(
        condicoes[0], "Aguardando cotacao/dados"
    ).mask(condicoes[1], "Oferta abaixo do mercado").mask(condicoes[2], "Melhor comprar na B3")
    metricas["status_viabilidade_oferta"] = metricas["status_viabilidade_oferta"].fillna("Precos equivalentes")
    metricas["atualizado_em"] = datetime.now()
    return metricas[
        [
            "cnpj",
            "ticker",
            "competencia",
            "patrimonio_liquido",
            "valor_cota_vpc",
            "preco_cota",
            "p_vp",
            "p_vp_emissao",
            "preco_emissao",
            "desconto_oferta_vp",
            "desconto_oferta_b3",
            "volume_medio_diario",
            "total_emissoes",
            "volume_total_ofertas",
            "coordenador_principal",
            "numero_cotistas",
            "taxa_administracao",
            "taxa_custodiante",
            "dividend_yield_mes",
            "dividend_yield_12m_historico",
            "rentabilidade_patrimonial_mes",
            "caixa_sobre_pl",
            "imoveis_sobre_pl",
            "cri_sobre_pl",
            "fii_sobre_pl",
            "passivo_sobre_pl",
            "vacancia_fisica",
            "vacancia_financeira",
            "numero_imoveis",
            "dividend_yield_12m",
            "status_viabilidade_oferta",
            "atualizado_em",
        ]
    ].dropna(subset=["cnpj"]).drop_duplicates("cnpj", keep="last")


