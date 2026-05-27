from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    import duckdb
except ImportError as exc:
    raise SystemExit(
        "DuckDB nao esta instalado. Rode `pip install -r requirements.txt` "
        "antes de gerar o warehouse."
    ) from exc

from database.build_common import (
    DATABASE_PATH,
    MANAGED_TABLES,
    PROCESSED_DATA_DIR,
    SCHEMA_PATH,
    _register_replace,
)
from database.builders import (
    _build_cotacoes,
    _build_dim_fii,
    _build_documento_extracoes,
    _build_documento_llm_extracoes,
    _build_informe,
    _build_macro,
    _build_metricas,
    _build_noticias,
    _build_oferta_inteligencia,
    _build_oferta_projecoes,
    _build_ofertas,
    _build_portfolio,
    _build_quality_report,
    _build_rendimentos,
    _combinar_extracoes_documento,
)


def build_database(database_path: Path = DATABASE_PATH) -> Path:
    """Gera o warehouse DuckDB a partir dos CSVs brutos e processados."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(database_path))
    for table in MANAGED_TABLES:
        con.execute(f"DROP TABLE IF EXISTS {table}")
    con.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

    ofertas = _build_ofertas()
    informe = _build_informe()
    cotacoes = _build_cotacoes()
    macro = _build_macro()
    noticias = _build_noticias()
    metricas = _build_metricas(informe, ofertas)
    dim_fii = _build_dim_fii(informe, metricas, ofertas)
    rendimentos = _build_rendimentos(informe, dim_fii)
    documento_extracoes = _build_documento_extracoes()
    documento_llm_extracoes = _build_documento_llm_extracoes()
    documento_extracoes_combinadas = _combinar_extracoes_documento(
        documento_extracoes,
        documento_llm_extracoes,
    )
    oferta_projecoes = _build_oferta_projecoes(ofertas, rendimentos, documento_extracoes_combinadas)
    oferta_inteligencia = _build_oferta_inteligencia(ofertas, metricas, oferta_projecoes)
    portfolio = _build_portfolio(informe)

    tables = {
        "dim_fii": dim_fii,
        "ofertas_cvm": ofertas,
        "fii_informe_mensal": informe,
        "fii_cotacoes": cotacoes,
        "fii_rendimentos": rendimentos,
        "fii_portfolio": portfolio,
        "macro_series": macro,
        "noticias_fiis": noticias,
        "fii_metricas": metricas,
        "oferta_projecoes": oferta_projecoes,
        "oferta_documento_extracoes": documento_extracoes,
        "oferta_documento_extracoes_llm": documento_llm_extracoes,
        "oferta_inteligencia": oferta_inteligencia,
    }
    for table, df in tables.items():
        _register_replace(con, table, df)

    quality = _build_quality_report(tables)
    _register_replace(con, "data_quality_report", quality)

    con.close()
    print(f"Warehouse gerado em: {database_path}")
    print(f"Tabelas carregadas: {', '.join(tables)}")
    return database_path


if __name__ == "__main__":
    build_database()
