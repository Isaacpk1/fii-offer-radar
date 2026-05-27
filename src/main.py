import sys
import argparse
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd


SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))
RAW_DATA_DIR = SRC_DIR / "data" / "raw"
PROCESSED_DATA_DIR = SRC_DIR / "data" / "processed"
WAREHOUSE_PATH = PROCESSED_DATA_DIR / "fii_warehouse.duckdb"
WAREHOUSE_REQUIRED_COLUMNS = {
    "oferta_inteligencia": [
        "confianca_total",
        "confianca_nivel",
        "confianca_dados",
        "confianca_sinais",
        "confianca_contexto",
        "confianca_resumo",
        "dados_ausentes_criticos",
    ]
}

from data_extraction import cvm_extractor, macro_extractor
from data_extraction.news import news_aggregator
from data_extraction import status_monitor
from data_extraction import fii_informe_extractor, fii_market_extractor
from data_processing import cleaner, enricher
from database import build_database


def _arquivo_de_hoje(path: Path) -> bool:
    return path.exists() and datetime.fromtimestamp(path.stat().st_mtime).date() == datetime.now().date()


def _arquivos_de_hoje(paths: list[Path]) -> bool:
    return all(_arquivo_de_hoje(path) for path in paths)


def _extrair_se_necessario(
    nome: str,
    func,
    saidas: list[Path],
    *,
    obrigatorio: bool = False,
    forcar: bool = False,
) -> bool:
    if not forcar and _arquivos_de_hoje(saidas):
        print(f"{nome}: dados de hoje ja existem. Etapa pulada.")
        return False

    try:
        resultado = func()
    except Exception as exc:
        if obrigatorio and not all(path.exists() for path in saidas):
            raise
        print(f"Aviso: {nome} falhou; usando arquivos locais existentes se disponiveis: {exc}")
        return False

    if resultado is None and obrigatorio and not all(path.exists() for path in saidas):
        raise RuntimeError(f"{nome} nao retornou dados e nao ha cache local utilizavel.")
    if resultado is None:
        print(f"Aviso: {nome} nao retornou dados novos; usando cache local se disponivel.")
        return False

    return True


def _carregar_ofertas_enriquecidas() -> pd.DataFrame | None:
    caminho = PROCESSED_DATA_DIR / "ofertas_fiis_pronto_para_ia.csv"
    if not caminho.exists():
        return None
    try:
        return pd.read_csv(caminho, sep=";", encoding="utf-8", low_memory=False)
    except Exception as exc:
        print(f"Aviso: nao foi possivel ler ofertas enriquecidas em cache: {exc}")
        return None


def _warehouse_schema_atualizado(path: Path = WAREHOUSE_PATH) -> bool:
    if not path.exists():
        return False

    try:
        with duckdb.connect(str(path), read_only=True) as con:
            for tabela, colunas_obrigatorias in WAREHOUSE_REQUIRED_COLUMNS.items():
                existente = con.execute(f"DESCRIBE {tabela}").df()
                colunas = set(existente["column_name"].astype(str))
                faltantes = [coluna for coluna in colunas_obrigatorias if coluna not in colunas]
                if faltantes:
                    print(
                        f"Warehouse: schema antigo em {tabela}; "
                        f"colunas faltantes: {', '.join(faltantes)}."
                    )
                    return False
        return True
    except Exception as exc:
        print(f"Warehouse: nao foi possivel validar schema atual: {exc}")
        return False


def executar_pipeline(forcar_atualizacao: bool = False):
    print("Iniciando o pipeline de dados do BTG Pactual...")
    alguma_fonte_atualizada = False

    print("\n--- Fase 1: Extracao de fontes ---")
    try:
        alguma_fonte_atualizada |= _extrair_se_necessario(
            "CVM Resolucao 160",
            cvm_extractor.baixar_dados_cvm,
            [RAW_DATA_DIR / "oferta_resolucao_160_bruto.csv"],
            obrigatorio=True,
            forcar=forcar_atualizacao,
        )
        alguma_fonte_atualizada |= _extrair_se_necessario(
            "Indicadores macro BCB",
            macro_extractor.obter_indicadores_macro,
            [RAW_DATA_DIR / "macro_bcb_bruto.csv", RAW_DATA_DIR / "selic_bruto.csv"],
            obrigatorio=True,
            forcar=forcar_atualizacao,
        )
        alguma_fonte_atualizada |= _extrair_se_necessario(
            "IFIX",
            macro_extractor.obter_ifix,
            [RAW_DATA_DIR / "ifix_bruto.csv"],
            forcar=forcar_atualizacao,
        )
    except Exception as e:
        print(f"Erro na extracao CVM/Macro: {e}")
        return

    ano_atual = datetime.now().year
    alguma_fonte_atualizada |= _extrair_se_necessario(
        "Informe mensal FII",
        fii_informe_extractor.baixar_informe_mensal,
        [RAW_DATA_DIR / f"informe_mensal_fii_{ano_atual}.csv"],
        forcar=forcar_atualizacao,
    )

    try:
        news_aggregator.agregar_noticias_sync()
    except Exception as e:
        print(f"Aviso: coleta de noticias falhou e sera ignorada: {e}")

    print("\n--- Fase 2: Limpeza e enriquecimento base ---")
    caminho_enriquecido = PROCESSED_DATA_DIR / "ofertas_fiis_pronto_para_ia.csv"
    if not forcar_atualizacao and not alguma_fonte_atualizada and _arquivo_de_hoje(caminho_enriquecido):
        print("Ofertas enriquecidas: dados de hoje ja existem. Etapa pulada.")
        df_enriquecido = _carregar_ofertas_enriquecidas()
    else:
        df_limpo = cleaner.limpar_dados_cvm()
        if df_limpo is None:
            print("Pipeline interrompido: limpeza da base CVM nao retornou dados.")
            return

        df_enriquecido = enricher.cruzar_cvm_com_macro(df_limpo)
        if df_enriquecido is None:
            print("Pipeline interrompido: enriquecimento macro nao retornou dados.")
            return
        alguma_fonte_atualizada = True

    if df_enriquecido is None or df_enriquecido.empty:
        print("Pipeline interrompido: ofertas enriquecidas indisponiveis.")
        return

    print("\n--- Fase 3: Monitor de status ---")
    try:
        alertas = status_monitor.verificar_mudancas_status()
        if alertas:
            print(f"{len(alertas)} mudanca(s) de status detectada(s):")
            for alerta in alertas:
                print(
                    f"  {alerta['Numero_Processo']}: "
                    f"{alerta['Status_Anterior']} -> {alerta['Status_Atual']}"
                )
        else:
            print("Nenhuma mudanca de status detectada.")

        if alertas:
            df_limpo = cleaner.limpar_dados_cvm()
            if df_limpo is not None:
                df_enriquecido = enricher.cruzar_cvm_com_macro(df_limpo)
                alguma_fonte_atualizada = True
    except Exception as e:
        print(f"Aviso: monitor de status falhou: {e}")

    print("\n--- Fase 4: Mercado e warehouse analitico ---")
    mercado_path = RAW_DATA_DIR / "fii_mercado_bruto.csv"
    if not forcar_atualizacao and _arquivo_de_hoje(mercado_path):
        print("Mercado B3: dados de hoje ja existem. Etapa pulada.")
    else:
        try:
            mercado = fii_market_extractor.buscar_mercado_por_cnpj(df_enriquecido)
            alguma_fonte_atualizada = alguma_fonte_atualizada or mercado is not None
        except Exception as e:
            print(f"Aviso: dados de mercado (yfinance) falharam; usando cache local se existir: {e}")

    schema_atualizado = _warehouse_schema_atualizado()
    if (
        not forcar_atualizacao
        and _arquivo_de_hoje(WAREHOUSE_PATH)
        and schema_atualizado
        and not alguma_fonte_atualizada
    ):
        print("Warehouse: arquivo de hoje ja existe. Etapa pulada.")
    else:
        try:
            build_database.build_database()
        except Exception as e:
            print(f"Aviso: geracao do warehouse DuckDB falhou: {e}")

    print("\nPipeline de dados concluido com sucesso.")
    print("A base final foi gerada para consumo pelo frontend e pelo agente de IA.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o pipeline de dados FII.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forca nova coleta mesmo quando os arquivos de saida ja foram gerados hoje.",
    )
    args = parser.parse_args()
    executar_pipeline(forcar_atualizacao=args.force)
