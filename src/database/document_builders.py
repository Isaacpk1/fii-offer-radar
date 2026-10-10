from __future__ import annotations

from datetime import datetime

import pandas as pd

from database.build_common import (
    PROCESSED_DATA_DIR,
    _ensure_columns,
    _read_csv,
    _to_datetime,
    _to_numeric,
)


def _build_documento_extracoes() -> pd.DataFrame:
    extracoes = _read_csv(PROCESSED_DATA_DIR / "oferta_documentos_extracoes.csv")
    if extracoes.empty:
        return pd.DataFrame()

    columns = [
        "numero_processo",
        "cnpj_emissor",
        "nome_emissor",
        "ticker",
        "tipo_documento",
        "fonte_url",
        "arquivo_path",
        "texto_path",
        "paginas_lidas",
        "caracteres_extraidos",
        "preco_emissao_extraido",
        "rendimento_mensal_projetado_por_cota",
        "rendimento_anual_projetado_por_cota",
        "dy_projetado_oferta",
        "taxa_administracao",
        "fonte_trecho",
        "confianca_extracao",
        "metodo",
        "status_extracao",
        "extraido_em",
        "observacao",
    ]
    extracoes = _ensure_columns(extracoes, columns)
    extracoes = _to_datetime(extracoes, ["extraido_em"])
    extracoes = _to_numeric(
        extracoes,
        [
            "paginas_lidas",
            "caracteres_extraidos",
            "preco_emissao_extraido",
            "rendimento_mensal_projetado_por_cota",
            "rendimento_anual_projetado_por_cota",
            "dy_projetado_oferta",
            "taxa_administracao",
            "confianca_extracao",
        ],
    )
    return extracoes


def _build_documento_llm_extracoes() -> pd.DataFrame:
    extracoes = _read_csv(PROCESSED_DATA_DIR / "oferta_documentos_extracoes_llm.csv")
    if extracoes.empty:
        return pd.DataFrame()

    columns = [
        "numero_processo",
        "cnpj_emissor",
        "nome_emissor",
        "ticker",
        "tipo_documento",
        "fonte_url",
        "arquivo_path",
        "texto_path",
        "preco_emissao",
        "rendimento_mensal_projetado_por_cota",
        "rendimento_anual_projetado_por_cota",
        "dy_projetado_oferta",
        "taxa_administracao",
        "indice_referencia",
        "spread_indice",
        "fonte_trecho",
        "confianca_extracao",
        "justificativa",
        "modelo",
        "status_extracao",
        "extraido_em",
        "observacao",
    ]
    extracoes = _ensure_columns(extracoes, columns)
    extracoes = _to_datetime(extracoes, ["extraido_em"])
    extracoes = _to_numeric(
        extracoes,
        [
            "preco_emissao",
            "rendimento_mensal_projetado_por_cota",
            "rendimento_anual_projetado_por_cota",
            "dy_projetado_oferta",
            "taxa_administracao",
            "spread_indice",
            "confianca_extracao",
        ],
    )
    return extracoes


def _combinar_extracoes_documento(
    documento_extracoes: pd.DataFrame,
    documento_llm_extracoes: pd.DataFrame,
) -> pd.DataFrame:
    frames = []
    if not documento_extracoes.empty:
        det = documento_extracoes.copy()
        det["origem_extracao"] = "deterministica"
        frames.append(det)

    if not documento_llm_extracoes.empty:
        llm = documento_llm_extracoes.rename(columns={"preco_emissao": "preco_emissao_extraido"}).copy()
        llm["paginas_lidas"] = pd.NA
        llm["caracteres_extraidos"] = pd.NA
        llm["metodo"] = "langchain_llm"
        llm["origem_extracao"] = "llm"
        frames.append(llm)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def _melhores_extracoes_documento(documento_extracoes: pd.DataFrame) -> pd.DataFrame:
    if documento_extracoes.empty:
        return pd.DataFrame()

    extracoes = documento_extracoes.copy()
    extracoes = extracoes[
        extracoes[
            [
                "preco_emissao_extraido",
                "rendimento_mensal_projetado_por_cota",
                "rendimento_anual_projetado_por_cota",
                "dy_projetado_oferta",
                "taxa_administracao",
            ]
        ]
        .notna()
        .any(axis=1)
    ]
    if extracoes.empty:
        return extracoes

    extracoes["prioridade_tipo"] = extracoes["tipo_documento"].map(
        {"prospecto": 4, "estudo_viabilidade": 4, "anuncio_inicio": 3, "aviso_mercado": 2}
    ).fillna(1)
    extracoes["prioridade_origem"] = extracoes.get("origem_extracao", pd.Series("", index=extracoes.index)).map(
        {"llm": 2, "deterministica": 1}
    ).fillna(0)

    linhas = []
    for numero_processo, grupo in extracoes.groupby("numero_processo"):
        grupo = grupo.sort_values(
            ["confianca_extracao", "prioridade_origem", "prioridade_tipo", "caracteres_extraidos"],
            ascending=[False, False, False, False],
        )
        linha = grupo.iloc[0].copy()

        for coluna in [
            "preco_emissao_extraido",
            "rendimento_mensal_projetado_por_cota",
            "rendimento_anual_projetado_por_cota",
            "dy_projetado_oferta",
            "taxa_administracao",
        ]:
            candidatos = grupo[grupo[coluna].notna()].sort_values(
                ["confianca_extracao", "prioridade_origem", "prioridade_tipo", "caracteres_extraidos"],
                ascending=[False, False, False, False],
            )
            if not candidatos.empty:
                linha[coluna] = candidatos.iloc[0][coluna]

        fontes = grupo[grupo["fonte_trecho"].notna()]["fonte_trecho"].astype(str).head(3)
        linha["numero_processo"] = numero_processo
        linha["fonte_trecho"] = " | ".join(fontes)[:1200]
        linha["confianca_extracao"] = grupo["confianca_extracao"].max()
        linhas.append(linha)

    return pd.DataFrame(linhas)


def _build_oferta_projecoes(
    ofertas: pd.DataFrame,
    rendimentos: pd.DataFrame,
    documento_extracoes: pd.DataFrame,
) -> pd.DataFrame:
    if ofertas.empty:
        return pd.DataFrame()

    base = _ensure_columns(
        ofertas,
        ["numero_processo", "cnpj_emissor", "data_requerimento", "preco_emissao"],
    ).copy()
    base = _to_datetime(base, ["data_requerimento"])
    base = _to_numeric(base, ["preco_emissao"])

    if not rendimentos.empty:
        hist = _ensure_columns(
            rendimentos,
            ["cnpj", "ticker", "data_com", "rendimento_por_cota"],
        ).copy()
        hist = _to_datetime(hist, ["data_com"])
        hist = _to_numeric(hist, ["rendimento_por_cota"])
        hist = hist.dropna(subset=["cnpj", "data_com", "rendimento_por_cota"])
        hist = hist[hist["rendimento_por_cota"] >= 0].sort_values(["cnpj", "data_com"])
    else:
        hist = pd.DataFrame(columns=["cnpj", "ticker", "data_com", "rendimento_por_cota"])

    historico_por_cnpj = {cnpj: grupo for cnpj, grupo in hist.groupby("cnpj")}
    melhores_docs = _melhores_extracoes_documento(documento_extracoes)
    docs_por_processo = (
        {row.numero_processo: row for row in melhores_docs.itertuples(index=False)}
        if not melhores_docs.empty
        else {}
    )
    linhas = []
    now = datetime.now()
    for row in base.itertuples(index=False):
        historico = historico_por_cnpj.get(row.cnpj_emissor)
        janela = pd.DataFrame()
        if historico is not None and pd.notna(row.data_requerimento):
            janela = historico[historico["data_com"] <= row.data_requerimento].tail(12)

        rendimento_12m = janela["rendimento_por_cota"].sum(min_count=1) if not janela.empty else pd.NA
        meses = int(janela["rendimento_por_cota"].notna().sum()) if not janela.empty else 0
        preco_emissao = row.preco_emissao
        doc = docs_por_processo.get(row.numero_processo)
        preco_doc = getattr(doc, "preco_emissao_extraido", pd.NA) if doc is not None else pd.NA
        preco_referencia = preco_emissao if pd.notna(preco_emissao) else preco_doc
        dy_historico = (
            rendimento_12m / preco_referencia
            if pd.notna(rendimento_12m) and pd.notna(preco_referencia) and preco_referencia > 0 and meses >= 3
            else pd.NA
        )
        dy_doc = getattr(doc, "dy_projetado_oferta", pd.NA) if doc is not None else pd.NA
        rendimento_anual_doc = (
            getattr(doc, "rendimento_anual_projetado_por_cota", pd.NA)
            if doc is not None
            else pd.NA
        )
        if pd.isna(dy_doc) and pd.notna(rendimento_anual_doc) and pd.notna(preco_referencia) and preco_referencia > 0:
            dy_doc = rendimento_anual_doc / preco_referencia
        if pd.notna(dy_doc) and not (0 < dy_doc < 0.5):
            dy_doc = pd.NA
            rendimento_anual_doc = pd.NA
        if pd.isna(rendimento_anual_doc) and pd.notna(dy_doc) and pd.notna(preco_referencia):
            rendimento_anual_doc = dy_doc * preco_referencia

        dy_projetado = dy_doc if pd.notna(dy_doc) else dy_historico
        rendimento_anual_projetado = (
            rendimento_anual_doc
            if pd.notna(rendimento_anual_doc)
            else (rendimento_12m if pd.notna(dy_historico) else pd.NA)
        )
        documento_tipo = getattr(doc, "tipo_documento", pd.NA) if doc is not None else pd.NA
        documento_url = getattr(doc, "fonte_url", pd.NA) if doc is not None else pd.NA
        documento_path = getattr(doc, "arquivo_path", pd.NA) if doc is not None else pd.NA
        fonte_trecho = getattr(doc, "fonte_trecho", pd.NA) if doc is not None else pd.NA
        confianca_extracao = getattr(doc, "confianca_extracao", pd.NA) if doc is not None else pd.NA
        if pd.isna(confianca_extracao) and pd.notna(dy_historico):
            confianca_extracao = 0.65 if meses >= 12 else 0.45
        metodo = (
            "documento_oferta"
            if pd.notna(dy_doc)
            else "historico_cvm_dy_mes_x_vpc_12m_sobre_preco_emissao"
        )
        ticker = janela["ticker"].dropna().iloc[-1] if not janela.empty and janela["ticker"].notna().any() else pd.NA
        if doc is not None and pd.isna(ticker):
            ticker = getattr(doc, "ticker", pd.NA)
        linhas.append(
            {
                "numero_processo": row.numero_processo,
                "cnpj_emissor": row.cnpj_emissor,
                "ticker": ticker,
                "data_requerimento": row.data_requerimento,
                "preco_emissao": preco_emissao,
                "rendimento_12m_historico_por_cota": rendimento_12m,
                "meses_historico_utilizados": meses,
                "dy_12m_historico_sobre_emissao": dy_historico,
                "dy_projetado_oferta": dy_projetado,
                "rendimento_anual_projetado_por_cota": rendimento_anual_projetado,
                "documento_tipo": documento_tipo,
                "documento_url": documento_url,
                "documento_path": documento_path,
                "fonte_trecho": fonte_trecho,
                "confianca_extracao": confianca_extracao,
                "metodo": metodo,
                "atualizado_em": now,
            }
        )

    return pd.DataFrame(linhas)


