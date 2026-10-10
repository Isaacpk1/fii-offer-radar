from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
from dotenv import load_dotenv
from langchain_classic.memory import ConversationBufferMemory
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from ai_core.tools import AGENT_TOOLS
except ModuleNotFoundError:
    from src.ai_core.tools import AGENT_TOOLS


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "src" / "data" / "processed" / "ofertas_fiis_pronto_para_ia.csv"
WAREHOUSE_PATH = PROJECT_ROOT / "src" / "data" / "processed" / "fii_warehouse.duckdb"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def _carregar_dataframe_agente() -> tuple[pd.DataFrame, str]:
    if WAREHOUSE_PATH.exists():
        with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
            df = con.execute("SELECT * FROM oferta_inteligencia").df()
        return df, "warehouse DuckDB: tabela oferta_inteligencia"

    try:
        df = pd.read_csv(CSV_PATH, sep=";", encoding="utf-8")
        return df, "CSV processado: ofertas_fiis_pronto_para_ia.csv"
    except Exception as e:
        raise Exception(
            "Erro ao carregar a base do agente. Rode `python src/main.py` ou "
            f"`python src/database/build_database.py`. Erro: {e}"
        )


def _resumo_contexto() -> str:
    if not WAREHOUSE_PATH.exists():
        return (
            "Warehouse ausente. O agente usara apenas o CSV processado, com menos contexto "
            "sobre VP/C, P/VP de emissao, score e qualidade da base."
        )

    try:
        with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
            resumo = con.execute(
                """
                SELECT
                    COUNT(*) AS total_ofertas,
                    COUNT(preco_emissao) AS com_preco_emissao,
                    COUNT(valor_cota_vpc) AS com_vpc,
                    COUNT(p_vp_emissao) AS com_p_vp_emissao,
                    COUNT(preco_cota_b3) AS com_preco_b3,
                    (SELECT COUNT(*) FROM noticias_fiis) AS noticias_contexto,
                    ROUND(AVG(cobertura_analise_percentual), 2) AS cobertura_media
                FROM oferta_inteligencia
                """
            ).fetchone()
        return (
            "Contexto carregado do warehouse: "
            f"{resumo[0]} ofertas; {resumo[1]} com preco de emissao; "
            f"{resumo[2]} com VP/C; {resumo[3]} com P/VP de emissao; "
            f"{resumo[4]} com preco B3; {resumo[5]} noticias de contexto; "
            f"cobertura media {resumo[6]}%."
        )
    except Exception as e:
        return f"Warehouse encontrado, mas o resumo de contexto falhou: {e}"


def inicializar_agente_analista(memory=None):
    """Inicializa o agente LangChain com contexto de ofertas primarias de FIIs."""
    print("Carregando o agente de IA do FII Offer Radar com Gemini...")

    df, fonte = _carregar_dataframe_agente()
    contexto = _resumo_contexto()

    modelo = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip().removeprefix("models/")
    llm = ChatGoogleGenerativeAI(model=modelo, temperature=0)
    instrucoes = f"""
    Voce e um analista financeiro senior, especialista em ofertas primarias de Fundos de Investimento Imobiliario (FIIs).
    Seu objetivo e ajudar a priorizar analises, explicar riscos e apontar lacunas de dados. Voce nao deve tratar o score como recomendacao de investimento.

    Fonte principal do DataFrame: {fonte}.
    {contexto}

    Colunas mais importantes quando o warehouse esta disponivel:
    - numero_processo, ticker, nome_emissor, nome_lider, status_requerimento e data_requerimento identificam a oferta.
    - preco_emissao e o preco da oferta primaria.
    - preco_cota_b3 e o preco negociado no mercado secundario quando o ticker foi mapeado.
    - valor_cota_vpc e o valor patrimonial por cota do informe mensal.
    - p_vp = preco_cota_b3 / valor_cota_vpc, ou seja, P/VP de mercado.
    - p_vp_emissao = preco_emissao / valor_cota_vpc, ou seja, P/VP da emissao. Este campo e crucial para ofertas primarias.
    - desconto_vs_b3 compara preco_emissao contra preco_cota_b3.
    - desconto_vs_vp compara preco_emissao contra valor_cota_vpc.
    - sinal_preco_b3, sinal_preco_vp, sinal_liquidez e sinal_historico resumem alertas da tese.
    - score_priorizacao e leitura_priorizacao ajudam a ordenar o trabalho, nao substituem decisao humana.
    - cobertura_analise_percentual indica se a conclusao esta bem suportada por dados.
    - confianca_total, confianca_nivel, confianca_dados, confianca_sinais, confianca_contexto e confianca_resumo medem a confianca auditavel da analise.

    Ferramentas disponiveis:
    - avaliar_confianca_analise: use antes de concluir sobre uma oferta especifica.
    - consultar_tese_oferta: use para analisar um numero de processo especifico.
    - buscar_noticias_contexto: use para trazer noticias por ticker, emissor, coordenador, setor ou tema.
    - rankear_ofertas_prioritarias: use para listar ofertas mais relevantes para triagem.
    - rankear_com_diagnostico: use quando a interface ou o usuario pedir ranking estruturado em JSON.
    - resumir_qualidade_base: use quando a pergunta envolver campos faltantes, confiabilidade ou cobertura.
    - resumir_mercado_ofertas: use para visao agregada por ano, status, lideres e macro.
    - buscar_macro_atual e calcular_spread_cdi: use apenas quando precisar de indicador atual.
    - gerar_brief_oferta: use quando o usuario pedir para gerar um brief persistente de uma oferta.
    - registrar_decisao_analista: use somente quando o usuario pedir explicitamente para registrar uma decisao.

    Regras de resposta:
    1. Responda em portugues do Brasil, com tom claro, analitico e executivo.
    2. Baseie as respostas nos dados disponiveis no DataFrame e nas ferramentas.
    3. Quando comparar oferta primaria, sempre diferencie P/VP de mercado (p_vp) de P/VP de emissao (p_vp_emissao).
    4. Cite lacunas importantes: ticker nao mapeado, preco B3 ausente, VP/C ausente, liquidez ausente ou baixa cobertura.
    5. Nao invente dados. Se a base nao tiver uma informacao, diga que ela nao esta disponivel e indique qual fonte/tabela precisa ser integrada.
    6. Para rankings, explique brevemente os sinais que puxaram a priorizacao.
    7. Use noticias apenas como contexto qualitativo e cite fonte/titulo quando elas influenciarem a leitura; nao trate noticia como dado financeiro auditado.
    8. Quando usar rankear_com_diagnostico, responda apenas com JSON valido no schema solicitado pela ferramenta.
    9. Regra critica de confianca: antes de emitir qualquer conclusao sobre uma oferta especifica, use avaliar_confianca_analise para essa oferta.
    10. Sempre apresente confianca assim: "Confianca da analise: [nivel] ([score]/100). Dados: [score_dados]/40; Sinais: [score_sinais]/35; Contexto: [score_contexto]/25." Cite dados ausentes e sinais conflitantes.
    11. Se a confianca for Insuficiente ou score < 30, diga que a analise nao deve ser usada para decisao. Se for Baixa ou score < 55, adicione aviso antes da conclusao.
    12. Evite aconselhamento de investimento; fale em priorizacao de analise, pontos de atencao e proximos checks.
    """

    memory = memory or ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
    )

    verbose = os.getenv("AGENT_VERBOSE", "false").strip().lower() in {"1", "true", "yes", "sim"}

    return create_pandas_dataframe_agent(
        llm=llm,
        df=df,
        extra_tools=AGENT_TOOLS,
        agent_executor_kwargs={"memory": memory},
        verbose=verbose,
        agent_type="tool-calling",
        prefix=instrucoes,
        allow_dangerous_code=True,
    )
