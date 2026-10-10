from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
PROCESSED_DATA_DIR = SRC_DIR / "data" / "processed"
DOCUMENTS_DIR = SRC_DIR / "data" / "raw" / "oferta_documentos"
WAREHOUSE_PATH = PROCESSED_DATA_DIR / "fii_warehouse.duckdb"
MANIFEST_PATH = PROCESSED_DATA_DIR / "oferta_documentos_manifest.csv"


def _carregar_ofertas_para_documentos() -> pd.DataFrame:
    try:
        import duckdb
    except ImportError as exc:
        raise SystemExit("DuckDB nao esta instalado. Rode `pip install -r requirements.txt`.") from exc

    if not WAREHOUSE_PATH.exists():
        raise FileNotFoundError(f"Warehouse nao encontrado: {WAREHOUSE_PATH}")

    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        return con.execute(
            """
            SELECT
                i.numero_processo,
                i.cnpj_emissor,
                i.ticker,
                i.nome_emissor,
                i.nome_lider,
                i.data_requerimento,
                i.valor_total_registrado,
                i.preco_emissao,
                i.dy_12m_historico_sobre_emissao,
                i.dy_projetado_oferta,
                i.score_priorizacao
            FROM oferta_inteligencia AS i
            WHERE i.preco_emissao IS NOT NULL
              AND i.dy_projetado_oferta IS NULL
            ORDER BY i.score_priorizacao DESC NULLS LAST, i.data_requerimento DESC
            """
        ).df()
    finally:
        con.close()


def gerar_manifesto_documentos_pendentes(limite: int | None = None) -> pd.DataFrame:
    """Gera uma fila auditavel para Playwright baixar prospectos e estudos de viabilidade."""
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    ofertas = _carregar_ofertas_para_documentos()
    if limite:
        ofertas = ofertas.head(limite)

    ofertas["consulta_fnet"] = (
        ofertas["nome_emissor"].fillna("")
        + " "
        + ofertas["ticker"].fillna("")
        + " prospecto oferta FII estudo de viabilidade"
    ).str.strip()
    ofertas["consulta_clube_fii"] = (
        ofertas["ticker"].fillna(ofertas["nome_emissor"]).fillna("")
        + " oferta publica FII rendimento projetado"
    ).str.strip()
    ofertas["diretorio_destino"] = ofertas["numero_processo"].astype(str).str.replace(
        r"[^A-Za-z0-9_-]+",
        "_",
        regex=True,
    ).map(lambda slug: str(DOCUMENTS_DIR / slug))
    ofertas["status_documento"] = "pendente_download"

    ofertas.to_csv(MANIFEST_PATH, sep=";", index=False, encoding="utf-8")
    print(f"Manifesto de documentos salvo em: {MANIFEST_PATH} ({len(ofertas)} ofertas)")
    return ofertas


if __name__ == "__main__":
    gerar_manifesto_documentos_pendentes()
