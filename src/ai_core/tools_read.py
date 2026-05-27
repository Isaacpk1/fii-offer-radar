from __future__ import annotations

from langchain.tools import tool

from ai_core.macro import obter_macro_atual
from ai_core.tool_config import CORE_COLUMNS
from ai_core.warehouse import (
    _carregar_base_csv,
    _normalizar_df,
    _query_warehouse,
    _select_existing_columns,
    _to_json,
    _tokens_busca,
    _warehouse_disponivel,
)


@tool
def buscar_macro_atual(indicador: str) -> str:
    """Retorna o valor mais recente de selic, ipca_12m, cdi ou usd_brl."""
    try:
        valor = obter_macro_atual(indicador)
        return f"{indicador.upper()} atual: {valor:.2f}"
    except Exception as e:
        return f"Nao foi possivel buscar o indicador macro: {e}"
@tool
def consultar_tese_oferta(numero_processo: str) -> str:
    """Consulta a tese completa de uma oferta em oferta_inteligencia pelo numero de processo CVM."""
    try:
        processo = numero_processo.strip().upper()
        cols = _select_existing_columns("oferta_inteligencia", CORE_COLUMNS)
        if not cols:
            return "Tabela oferta_inteligencia sem colunas reconhecidas para consulta."
        df = _query_warehouse(
            f"""
            SELECT {", ".join(cols)}
            FROM oferta_inteligencia
            WHERE UPPER(CAST(numero_processo AS VARCHAR)) = ?
            """,
            [processo],
        )
        if df.empty:
            return f"Nenhuma tese encontrada para o processo {numero_processo}."
        return _to_json(df)
    except Exception as e:
        return f"Erro ao consultar tese da oferta: {e}"
@tool
def buscar_noticias_contexto(consulta: str) -> str:
    """Busca noticias recentes por ticker, emissor, coordenador, setor ou tema para contextualizar uma analise."""
    try:
        tokens = _tokens_busca(consulta)
        if not tokens:
            return "Informe um ticker, emissor, coordenador, setor ou tema para buscar noticias."

        where = " OR ".join(["texto_busca LIKE ?" for _ in tokens])
        params = [f"%{token}%" for token in tokens]
        df = _query_warehouse(
            f"""
            SELECT fonte, titulo, data_publicacao, resumo, url
            FROM noticias_fiis
            WHERE {where}
            ORDER BY coletado_em DESC NULLS LAST, data_publicacao DESC NULLS LAST
            LIMIT 10
            """,
            params,
        )
        if df.empty:
            return f"Nenhuma noticia encontrada para: {consulta}."
        return _to_json(df)
    except Exception as e:
        return f"Erro ao buscar noticias de contexto: {e}"
@tool
def resumir_qualidade_base(tabela: str = "oferta_inteligencia") -> str:
    """Resume cobertura de dados por coluna para uma tabela do warehouse."""
    try:
        nome_tabela = tabela.strip().lower() or "oferta_inteligencia"
        df = _query_warehouse(
            """
            SELECT tabela, coluna, total_linhas, valores_preenchidos,
                   cobertura_percentual, observacao
            FROM data_quality_report
            WHERE LOWER(tabela) = ?
            ORDER BY cobertura_percentual ASC, coluna
            LIMIT 25
            """,
            [nome_tabela],
        )
        if df.empty:
            return f"Nao ha relatorio de qualidade para a tabela {tabela}."
        return _to_json(df)
    except Exception as e:
        return f"Erro ao resumir qualidade da base: {e}"
@tool
def resumir_mercado_ofertas(ano: str = "") -> str:
    """Resume o mercado de ofertas por ano opcional, com volume, status, coordenadores e macro medio."""
    try:
        filtro = ""
        params: list = []
        ano_limpo = str(ano).strip()
        if ano_limpo:
            filtro = "WHERE EXTRACT(year FROM data_requerimento) = ?"
            params.append(int(ano_limpo))

        resumo = _query_warehouse(
            f"""
            SELECT
                COUNT(*) AS total_ofertas,
                SUM(valor_total_registrado) AS volume_total_registrado,
                AVG(CASE WHEN isfinite(preco_emissao) THEN preco_emissao END) AS preco_emissao_medio,
                MEDIAN(CASE WHEN isfinite(p_vp_emissao) THEN p_vp_emissao END) AS p_vp_emissao_mediano,
                MEDIAN(CASE WHEN isfinite(desconto_vs_b3) THEN desconto_vs_b3 END) AS desconto_vs_b3_mediano,
                MEDIAN(CASE WHEN isfinite(desconto_vs_vp) THEN desconto_vs_vp END) AS desconto_vs_vp_mediano,
                AVG(CASE WHEN isfinite(taxa_selic_data_oferta) THEN taxa_selic_data_oferta END) AS selic_media,
                AVG(CASE WHEN isfinite(cdi_data_oferta) THEN cdi_data_oferta END) AS cdi_medio,
                AVG(CASE WHEN isfinite(pontos_ifix_data_oferta) THEN pontos_ifix_data_oferta END) AS ifix_medio,
                AVG(CASE WHEN isfinite(cobertura_analise_percentual) THEN cobertura_analise_percentual END) AS cobertura_media
            FROM oferta_inteligencia
            {filtro}
            """,
            params,
        )
        status = _query_warehouse(
            f"""
            SELECT status_requerimento, COUNT(*) AS ofertas,
                   SUM(valor_total_registrado) AS volume_total_registrado
            FROM oferta_inteligencia
            {filtro}
            GROUP BY status_requerimento
            ORDER BY ofertas DESC
            LIMIT 10
            """,
            params,
        )
        lideres = _query_warehouse(
            f"""
            SELECT nome_lider, COUNT(*) AS ofertas,
                   SUM(valor_total_registrado) AS volume_total_registrado
            FROM oferta_inteligencia
            {filtro}
            GROUP BY nome_lider
            ORDER BY volume_total_registrado DESC NULLS LAST
            LIMIT 10
            """,
            params,
        )
        return (
            '{"resumo":'
            + _to_json(resumo)
            + ',"status":'
            + _to_json(status)
            + ',"lideres":'
            + _to_json(lideres)
            + "}"
        )
    except Exception as e:
        return f"Erro ao resumir mercado de ofertas: {e}"
@tool
def consultar_oferta_cvm(numero_processo: str) -> str:
    """Consulta uma oferta pelo Numero_Processo da CVM, priorizando a tese enriquecida do warehouse."""
    try:
        if _warehouse_disponivel():
            return consultar_tese_oferta.invoke(numero_processo)

        df = _carregar_base_csv()
        filtro = df["Numero_Processo"].astype(str).str.upper() == numero_processo.strip().upper()
        oferta = df[filtro]
        if oferta.empty:
            return f"Nenhuma oferta encontrada para o processo {numero_processo}."
        return _normalizar_df(oferta.head(1)).to_json(orient="records", force_ascii=False)
    except Exception as e:
        return f"Erro ao consultar oferta CVM: {e}"
@tool
def calcular_spread_cdi(taxa_percentual: str) -> str:
    """Calcula o spread, em pontos percentuais, entre uma taxa informada e o CDI atual."""
    try:
        taxa = float(str(taxa_percentual).replace("%", "").replace(",", ".").strip())
        cdi = obter_macro_atual("cdi")
        spread = taxa - cdi
        return f"Taxa informada: {taxa:.2f}%. CDI atual: {cdi:.2f}%. Spread: {spread:.2f} p.p."
    except Exception as e:
        return f"Erro ao calcular spread sobre CDI: {e}"
