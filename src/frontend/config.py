from pathlib import Path
import sys


SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_DIR.parent
PROCESSED_DATA_DIR = SRC_DIR / "data" / "processed"
WAREHOUSE_PATH = PROCESSED_DATA_DIR / "fii_warehouse.duckdb"
OFERTAS_PATH = PROCESSED_DATA_DIR / "ofertas_fiis_pronto_para_ia.csv"
ANALISE_FII_PATH = PROCESSED_DATA_DIR / "fii_analise_completa.csv"
STATUS_ALERTS_PATH = PROCESSED_DATA_DIR / "status_monitor_alerts.json"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

BTG_BLUE = "#002F6C"
INK = "#172033"
MUTED = "#667085"
LINE = "#D9E2EC"
SURFACE = "#F7F9FC"
GREEN = "#0F8B6B"
RED = "#C43D4B"
AMBER = "#B7791F"
TEAL = "#00A3A3"

TABLE_LABELS = {
    "dim_fii": "Cadastro de FIIs",
    "ofertas_cvm": "Ofertas CVM 160",
    "oferta_inteligencia": "Inteligencia da oferta",
    "oferta_projecoes": "Projecoes da oferta",
    "oferta_documento_extracoes": "Extracao deterministica",
    "oferta_documento_extracoes_llm": "Extracao via IA",
    "fii_informe_mensal": "Informe mensal",
    "fii_cotacoes": "Cotacoes e liquidez",
    "fii_rendimentos": "Rendimentos",
    "fii_portfolio": "Portfolio e operacao",
    "macro_series": "Macro e IFIX",
    "fii_metricas": "Metricas comparativas",
    "data_quality_report": "Qualidade dos dados",
}

TAPI_STEPS = [
    {
        "titulo": "Coleta automatizada",
        "texto": "CVM, Banco Central, yfinance e scrapers de noticias entram no pipeline.",
        "status": "Implementado",
    },
    {
        "titulo": "Documentos de oferta",
        "texto": "PDFs de anuncios, prospectos e comunicados ficam catalogados por processo.",
        "status": "Implementado",
    },
    {
        "titulo": "Extracao deterministica",
        "texto": "Regex e validacoes capturam campos objetivos quando o PDF esta bem estruturado.",
        "status": "Implementado",
    },
    {
        "titulo": "Extracao semantica",
        "texto": "LangChain interpreta guidance, rendimento alvo e tabelas quebradas quando o regex nao basta.",
        "status": "Parcial",
    },
    {
        "titulo": "Tese da oferta",
        "texto": "Cada processo CVM vira uma tese com preco, liquidez, historico, macro e DY projetado.",
        "status": "Implementado",
    },
    {
        "titulo": "Copiloto analitico",
        "texto": "O agente conversa com o warehouse e explica os sinais para a decisao.",
        "status": "Implementado",
    },
]
