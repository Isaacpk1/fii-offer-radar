from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

import duckdb
from langchain.tools import tool

from ai_core.tool_config import BRIEFS_DIR, WAREHOUSE_PATH
from ai_core.tools_read import buscar_macro_atual, buscar_noticias_contexto, consultar_tese_oferta


@tool
def gerar_brief_oferta(numero_processo: str) -> str:
    """
    Gera e salva um brief de investimento em JSON para uma oferta especifica.
    Use quando o usuario pedir para gerar o brief ou preparar a analise de uma oferta.
    """
    try:
        processo = numero_processo.strip()
        dados = consultar_tese_oferta.invoke(processo)
        noticias = buscar_noticias_contexto.invoke(processo)
        macro_selic = buscar_macro_atual.invoke("selic")
        macro_cdi = buscar_macro_atual.invoke("cdi")

        try:
            dados_oferta = json.loads(dados)
        except json.JSONDecodeError:
            dados_oferta = {"raw": dados}
        try:
            noticias_contexto = json.loads(noticias)
        except json.JSONDecodeError:
            noticias_contexto = {"raw": noticias}

        brief = {
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "numero_processo": processo,
            "dados_oferta": dados_oferta,
            "noticias_contexto": noticias_contexto,
            "contexto_macro": {
                "selic": macro_selic,
                "cdi": macro_cdi,
            },
            "status": "rascunho",
            "proximo_passo": "Revisar P/VP de emissao, desconto vs B3, DY projetado e cobertura de dados.",
        }

        BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
        slug = processo.replace("/", "_").replace("\\", "_").replace(" ", "_")
        caminho = BRIEFS_DIR / f"brief_{slug}.json"
        caminho.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"Brief gerado e salvo em: {caminho}. Proximo passo: revisar p_vp_emissao e cobertura de dados."
    except Exception as e:
        return f"Erro ao gerar brief: {e}"
@tool
def registrar_decisao_analista(
    numero_processo: str,
    decisao: Literal["aprovar", "rejeitar", "pendente"],
    justificativa: str,
) -> str:
    """
    Registra a decisao do analista no warehouse.
    Use decisao como aprovar, rejeitar ou pendente.
    """
    try:
        if not justificativa.strip():
            return "Justificativa obrigatoria para registrar a decisao."
        with duckdb.connect(str(WAREHOUSE_PATH)) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS decisoes_analista (
                    numero_processo VARCHAR,
                    decisao VARCHAR,
                    justificativa TEXT,
                    registrado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            con.execute(
                "INSERT INTO decisoes_analista VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                [numero_processo.strip(), decisao, justificativa.strip()],
            )
        return f"Decisao '{decisao}' registrada para {numero_processo}."
    except Exception as e:
        return f"Erro ao registrar decisao: {e}"
