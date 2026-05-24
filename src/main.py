import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))

from data_extraction import cvm_extractor, macro_extractor
from data_processing import cleaner, enricher


def executar_pipeline():
    print("Iniciando o pipeline de dados do BTG Pactual...")

    print("\n--- Fase 1: Extracao ---")
    try:
        cvm_extractor.baixar_dados_cvm()
        macro_extractor.obter_indicadores_macro()
        macro_extractor.obter_ifix()
    except Exception as e:
        print(f"Erro na extracao: {e}")
        return

    print("\n--- Fase 2: Limpeza e Enriquecimento ---")
    df_limpo = cleaner.limpar_dados_cvm()

    if df_limpo is not None:
        enricher.cruzar_cvm_com_macro(df_limpo)
        print("\nPipeline de dados concluido com sucesso.")
        print("A base final foi gerada para consumo pelo frontend e pelo agente de IA.")


if __name__ == "__main__":
    executar_pipeline()
