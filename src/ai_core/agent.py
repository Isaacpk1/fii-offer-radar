from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "src" / "data" / "processed" / "ofertas_fiis_pronto_para_ia.csv"


def inicializar_agente_analista():
    """Inicializa o agente LangChain especializado nos dados da CVM e macroeconomia."""
    print("Carregando o agente de IA do BTG Pactual com Gemini...")

    try:
        df = pd.read_csv(CSV_PATH, sep=";", encoding="utf-8")
    except Exception as e:
        raise Exception(f"Erro ao carregar o CSV. Rode o pipeline de dados primeiro. Erro: {e}")

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    instrucoes = """
    Voce e um analista financeiro senior do banco BTG Pactual, especialista em ofertas primarias de Fundos de Investimento Imobiliario (FIIs).
    Voce tem acesso a um DataFrame do Pandas com dados oficiais da Resolucao CVM 160.
    Os dados ja estao cruzados com a Taxa Selic e o IFIX da data de cada oferta.

    Regras de ouro para as suas respostas:
    1. Baseie-se SEMPRE nos dados do DataFrame.
    2. Sempre que possivel, correlacione o volume financeiro ou o status das ofertas com o cenario macroeconomico.
    3. Responda em portugues do Brasil, de forma clara, corporativa e analitica.
    4. Nao invente dados. Se a informacao nao estiver no dataframe, diga que nao tem essa informacao.
    """

    return create_pandas_dataframe_agent(
        llm=llm,
        df=df,
        verbose=True,
        agent_type="tool-calling",
        prefix=instrucoes,
        allow_dangerous_code=True,
    )
