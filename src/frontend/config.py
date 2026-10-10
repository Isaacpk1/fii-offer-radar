import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_DIR.parent
PROCESSED_DATA_DIR = SRC_DIR / "data" / "processed"
# Snapshot versionado para a demo publica: usado so quando o pipeline local
# ainda nao gerou a base em src/data/processed.
DEMO_DATA_DIR = PROJECT_ROOT / "demo"


def _com_fallback_demo(nome: str) -> Path:
    local = PROCESSED_DATA_DIR / nome
    demo = DEMO_DATA_DIR / nome
    return local if local.exists() or not demo.exists() else demo


WAREHOUSE_PATH = _com_fallback_demo("fii_warehouse.duckdb")
OFERTAS_PATH = _com_fallback_demo("ofertas_fiis_pronto_para_ia.csv")
USANDO_DEMO = WAREHOUSE_PATH.parent == DEMO_DATA_DIR
STATUS_ALERTS_PATH = PROCESSED_DATA_DIR / "status_monitor_alerts.json"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

BRAND_BLUE = "#002F6C"
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
