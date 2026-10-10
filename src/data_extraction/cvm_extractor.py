import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "src" / "data" / "raw"


def baixar_dados_cvm():
    """Baixa e extrai o arquivo de ofertas da Resolucao 160 da CVM."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    url = "https://dados.cvm.gov.br/dados/OFERTA/DISTRIB/DADOS/oferta_distribuicao.zip"
    print(f"Baixando dados da CVM: {url}")

    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            arquivos_csv = [nome for nome in zf.namelist() if nome.endswith(".csv")]
            arquivo_alvo = next(
                (nome for nome in arquivos_csv if nome.lower().endswith("oferta_resolucao_160.csv")),
                None,
            )
            if arquivo_alvo is None:
                candidatos = [
                    nome for nome in arquivos_csv
                    if "resolucao_160" in nome.lower() or "oferta" in nome.lower()
                ]
                arquivo_alvo = candidatos[0] if candidatos else arquivos_csv[0]
            print(f"Extraindo o arquivo: {arquivo_alvo}")

            with zf.open(arquivo_alvo) as arquivo:
                df = pd.read_csv(
                    arquivo,
                    sep=";",
                    encoding="latin-1",
                    engine="python",
                    on_bad_lines="skip",
                )

        caminho_saida = RAW_DATA_DIR / "oferta_resolucao_160_bruto.csv"
        df.to_csv(caminho_saida, sep=";", index=False, encoding="utf-8")

        print(f"Dados da CVM salvos em: {caminho_saida} ({len(df)} registros)")
        return df

    except Exception as e:
        print(f"Erro ao extrair dados da CVM: {e}")
        return None


if __name__ == "__main__":
    baixar_dados_cvm()
