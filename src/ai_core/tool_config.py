from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = PROJECT_ROOT / "src" / "data" / "processed"
DEMO_DATA_DIR = PROJECT_ROOT / "demo"


def _com_fallback_demo(nome: str) -> Path:
    local = PROCESSED_DATA_DIR / nome
    demo = DEMO_DATA_DIR / nome
    return local if local.exists() or not demo.exists() else demo


CSV_PATH = _com_fallback_demo("ofertas_fiis_pronto_para_ia.csv")
WAREHOUSE_PATH = _com_fallback_demo("fii_warehouse.duckdb")
BRIEFS_DIR = PROJECT_ROOT / "src" / "data" / "briefs"

MACRO_CODES = {
    "selic": 11,
    "ipca": 13522,
    "ipca_12m": 13522,
    "cdi": 12,
    "usd_brl": 1,
    "dolar": 1,
}

CORE_COLUMNS = [
    "numero_processo",
    "ticker",
    "nome_emissor",
    "nome_lider",
    "data_requerimento",
    "status_requerimento",
    "valor_total_registrado",
    "preco_emissao",
    "preco_cota_b3",
    "valor_cota_vpc",
    "p_vp",
    "p_vp_emissao",
    "desconto_vs_b3",
    "desconto_vs_vp",
    "volume_medio_diario",
    "sinal_preco_b3",
    "sinal_preco_vp",
    "sinal_liquidez",
    "sinal_historico",
    "score_priorizacao",
    "leitura_priorizacao",
    "cobertura_analise_percentual",
    "confianca_total",
    "confianca_nivel",
    "confianca_dados",
    "confianca_sinais",
    "confianca_contexto",
    "confianca_resumo",
    "dados_ausentes_criticos",
]
