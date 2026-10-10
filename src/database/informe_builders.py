from __future__ import annotations

import pandas as pd

from database.build_common import (
    RAW_DATA_DIR,
    _coalesce_duplicate_columns,
    _ensure_columns,
    _normalizar_yield_mensal,
    _read_csv,
    _to_datetime,
    _to_numeric,
)


def _build_informe() -> pd.DataFrame:
    arquivos = sorted(RAW_DATA_DIR.glob("informe_mensal_fii_*.csv"))
    if not arquivos:
        return pd.DataFrame()

    informe = pd.concat([_read_csv(path) for path in arquivos], ignore_index=True)
    rename = {
        "CNPJ_Fundo": "cnpj",
        "CNPJ_Fundo_Classe": "cnpj",
        "Competencia": "competencia",
        "Data_Referencia": "competencia",
        "Nome_Fundo": "nome_fundo",
        "Nome_Fundo_Classe": "nome_fundo",
        "Patrimonio_Liquido": "patrimonio_liquido",
        "VL_Patrim_Liq": "patrimonio_liquido",
        "Valor_Cota_VPC": "valor_cota_vpc",
        "Valor_Patrimonial_Cotas": "valor_cota_vpc",
        "VL_Cota": "valor_cota_vpc",
        "Numero_Cotistas": "numero_cotistas",
        "Total_Numero_Cotistas": "numero_cotistas",
        "NR_Cotst": "numero_cotistas",
        "Numero_Cotistas_Pessoa_Fisica": "numero_cotistas_pessoa_fisica",
        "Numero_Cotistas_Pessoa_Juridica_Nao_Financeira": "numero_cotistas_pessoa_juridica",
        "Numero_Cotistas_Investidores_Nao_Residentes": "numero_cotistas_investidores_nao_residentes",
        "Total_Investido": "total_ativos",
        "Valor_Ativo": "total_ativos",
        "VL_Total": "total_ativos",
        "Total_Passivo": "total_passivo",
        "Disponibilidades": "disponibilidades",
        "Taxa_Administracao": "taxa_administracao",
        "Taxa_Custodiante": "taxa_custodiante",
        "Dividend_Yield_Mes": "dividend_yield_mes",
        "Rentabilidade_Efetiva_Mes": "rentabilidade_efetiva_mes",
        "Rentabilidade_Patrimonial_Mes": "rentabilidade_patrimonial_mes",
        "Amortizacao_Cotas_Mes": "amortizacao_cotas_mes",
        "Segmento_Atuacao": "segmento_atuacao",
        "Tipo_Gestao": "tipo_gestao",
        "Publico_Alvo": "publico_alvo_fundo",
        "Codigo_ISIN": "codigo_isin",
        "Mandato": "mandato",
        "Prazo_Duracao": "prazo_duracao",
        "Mercado_Negociacao_Bolsa": "mercado_negociacao_bolsa",
        "Mercado_Negociacao_MBO": "mercado_negociacao_mbo",
        "Mercado_Negociacao_MB": "mercado_negociacao_mb",
        "Nome_Administrador": "nome_administrador",
        "CNPJ_Administrador": "cnpj_administrador",
        "Site": "site",
        "Email": "email",
        "Direitos_Bens_Imoveis": "direitos_bens_imoveis",
        "Imoveis_Renda_Acabados": "imoveis_renda_acabados",
        "Imoveis_Renda_Construcao": "imoveis_renda_construcao",
        "Imoveis_Venda_Acabados": "imoveis_venda_acabados",
        "Imoveis_Venda_Construcao": "imoveis_venda_construcao",
        "Ativo_FII": "ativo_fii",
        "CRI": "cri",
        "CRI_CRA": "cri_cra",
        "LCI": "lci",
        "LCI_LCA": "lci_lca",
        "LIG": "lig",
        "Titulos_Publicos": "titulos_publicos",
        "Titulos_Privados": "titulos_privados",
        "Fundos_Renda_Fixa": "fundos_renda_fixa",
        "Rendimentos_Distribuir": "rendimentos_distribuir",
        "Taxa_Administracao_Pagar": "taxa_administracao_pagar",
        "Taxa_Performance_Pagar": "taxa_performance_pagar",
    }
    informe = informe.rename(columns={k: v for k, v in rename.items() if k in informe.columns})
    informe = _coalesce_duplicate_columns(informe)
    columns = [
        "cnpj",
        "competencia",
        "patrimonio_liquido",
        "valor_cota_vpc",
        "numero_cotistas",
        "numero_cotistas_pessoa_fisica",
        "numero_cotistas_pessoa_juridica",
        "numero_cotistas_investidores_nao_residentes",
        "total_ativos",
        "total_passivo",
        "disponibilidades",
        "taxa_administracao",
        "taxa_custodiante",
        "dividend_yield_mes",
        "rentabilidade_efetiva_mes",
        "rentabilidade_patrimonial_mes",
        "amortizacao_cotas_mes",
        "nome_fundo",
        "segmento_atuacao",
        "tipo_gestao",
        "publico_alvo_fundo",
        "codigo_isin",
        "mandato",
        "prazo_duracao",
        "mercado_negociacao_bolsa",
        "mercado_negociacao_mbo",
        "mercado_negociacao_mb",
        "nome_administrador",
        "cnpj_administrador",
        "site",
        "email",
        "total_investido",
        "direitos_bens_imoveis",
        "imoveis_renda_acabados",
        "imoveis_renda_construcao",
        "imoveis_venda_acabados",
        "imoveis_venda_construcao",
        "ativo_fii",
        "cri",
        "cri_cra",
        "lci",
        "lci_lca",
        "lig",
        "titulos_publicos",
        "titulos_privados",
        "fundos_renda_fixa",
        "rendimentos_distribuir",
        "taxa_administracao_pagar",
        "taxa_performance_pagar",
    ]
    informe = _ensure_columns(informe, columns)
    informe = _to_datetime(informe, ["competencia"])
    numeric_columns = [
        col for col in columns
        if col not in {
            "cnpj",
            "competencia",
            "nome_fundo",
            "segmento_atuacao",
            "tipo_gestao",
            "publico_alvo_fundo",
            "codigo_isin",
            "mandato",
            "prazo_duracao",
            "mercado_negociacao_bolsa",
            "mercado_negociacao_mbo",
            "mercado_negociacao_mb",
            "nome_administrador",
            "cnpj_administrador",
            "site",
            "email",
        }
    ]
    informe = _to_numeric(informe, numeric_columns)
    pl = informe["patrimonio_liquido"].where(informe["patrimonio_liquido"] > 0)
    total_imoveis = informe[
        [
            "direitos_bens_imoveis",
            "imoveis_renda_acabados",
            "imoveis_renda_construcao",
            "imoveis_venda_acabados",
            "imoveis_venda_construcao",
        ]
    ].sum(axis=1, min_count=1)
    informe["caixa_sobre_pl"] = informe["disponibilidades"] / pl
    informe["imoveis_sobre_pl"] = total_imoveis / pl
    total_cri = informe[["cri", "cri_cra"]].sum(axis=1, min_count=1)
    informe["cri_sobre_pl"] = total_cri / pl
    informe["fii_sobre_pl"] = informe["ativo_fii"] / pl
    informe["passivo_sobre_pl"] = informe["total_passivo"] / pl
    informe["fonte"] = "CVM Informe Mensal FII"
    return informe.dropna(subset=["cnpj", "competencia"]).drop_duplicates(
        ["cnpj", "competencia"], keep="last"
    )


def _build_rendimentos(informe: pd.DataFrame, dim_fii: pd.DataFrame) -> pd.DataFrame:
    if informe.empty:
        return pd.DataFrame()

    rendimentos = _ensure_columns(
        informe,
        ["cnpj", "competencia", "valor_cota_vpc", "dividend_yield_mes"],
    ).copy()
    rendimentos = rendimentos.dropna(subset=["cnpj", "competencia"])
    rendimentos["valor_cota_base"] = pd.to_numeric(rendimentos["valor_cota_vpc"], errors="coerce")
    rendimentos["dividend_yield_mes"] = _normalizar_yield_mensal(rendimentos["dividend_yield_mes"])
    rendimentos["rendimento_por_cota"] = (
        rendimentos["dividend_yield_mes"] * rendimentos["valor_cota_base"].where(rendimentos["valor_cota_base"] > 0)
    )
    rendimentos = rendimentos.sort_values(["cnpj", "competencia"])
    rendimentos["dividend_yield_12m"] = (
        rendimentos.groupby("cnpj")["dividend_yield_mes"]
        .rolling(12, min_periods=3)
        .sum()
        .reset_index(level=0, drop=True)
    )
    if not dim_fii.empty and {"cnpj", "ticker"}.issubset(dim_fii.columns):
        rendimentos = rendimentos.merge(dim_fii[["cnpj", "ticker"]], on="cnpj", how="left")
    else:
        rendimentos["ticker"] = pd.NA
    rendimentos["data_com"] = rendimentos["competencia"]
    rendimentos["data_pagamento"] = rendimentos["competencia"]
    rendimentos["metodo_estimativa"] = "Dividend_Yield_Mes_CVM_x_Valor_Cota_VPC"
    rendimentos["fonte"] = "CVM Informe Mensal FII"
    return rendimentos[
        [
            "ticker",
            "cnpj",
            "data_com",
            "data_pagamento",
            "rendimento_por_cota",
            "valor_cota_base",
            "dividend_yield_mes",
            "dividend_yield_12m",
            "metodo_estimativa",
            "fonte",
        ]
    ].drop_duplicates(["ticker", "cnpj", "data_com", "data_pagamento"], keep="last")


def _build_portfolio(informe: pd.DataFrame) -> pd.DataFrame:
    if informe.empty:
        return pd.DataFrame()

    portfolio = _ensure_columns(
        informe,
        [
            "cnpj",
            "competencia",
            "imoveis_sobre_pl",
            "cri_sobre_pl",
            "lci",
            "lci_lca",
            "fii_sobre_pl",
            "caixa_sobre_pl",
            "titulos_publicos",
            "titulos_privados",
            "fundos_renda_fixa",
            "passivo_sobre_pl",
            "patrimonio_liquido",
        ],
    ).copy()
    pl = portfolio["patrimonio_liquido"].where(portfolio["patrimonio_liquido"] > 0)
    portfolio["numero_imoveis"] = pd.NA
    portfolio["vacancia_fisica"] = pd.NA
    portfolio["vacancia_financeira"] = pd.NA
    portfolio["perfil_inquilinos"] = pd.NA
    portfolio["exposicao_imoveis"] = portfolio["imoveis_sobre_pl"]
    portfolio["exposicao_cri"] = portfolio["cri_sobre_pl"]
    total_lci = portfolio[["lci", "lci_lca"]].sum(axis=1, min_count=1)
    portfolio["exposicao_lci"] = total_lci / pl
    portfolio["exposicao_fii"] = portfolio["fii_sobre_pl"]
    portfolio["exposicao_caixa"] = portfolio["caixa_sobre_pl"]
    portfolio["exposicao_titulos_publicos"] = portfolio["titulos_publicos"] / pl
    portfolio["exposicao_titulos_privados"] = portfolio["titulos_privados"] / pl
    portfolio["exposicao_renda_fixa"] = portfolio["fundos_renda_fixa"] / pl
    portfolio["fonte"] = "CVM Informe Mensal FII - Ativo/Passivo"
    return portfolio[
        [
            "cnpj",
            "competencia",
            "numero_imoveis",
            "vacancia_fisica",
            "vacancia_financeira",
            "perfil_inquilinos",
            "exposicao_imoveis",
            "exposicao_cri",
            "exposicao_lci",
            "exposicao_fii",
            "exposicao_caixa",
            "exposicao_titulos_publicos",
            "exposicao_titulos_privados",
            "exposicao_renda_fixa",
            "passivo_sobre_pl",
            "fonte",
        ]
    ].dropna(subset=["cnpj", "competencia"]).drop_duplicates(["cnpj", "competencia"], keep="last")


