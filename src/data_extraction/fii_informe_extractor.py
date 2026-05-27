import io
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "src" / "data" / "raw"
BASE_URL = "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS"

COLUNAS_GERAL = {
    "Tipo_Fundo_Classe": "Tipo_Fundo_Classe",
    "CNPJ_Fundo": "CNPJ_Fundo",
    "CNPJ_Fundo_Classe": "CNPJ_Fundo",
    "Data_Referencia": "Competencia",
    "Competencia": "Competencia",
    "Data_Entrega": "Data_Entrega",
    "Nome_Fundo_Classe": "Nome_Fundo",
    "Data_Funcionamento": "Data_Funcionamento",
    "Publico_Alvo": "Publico_Alvo",
    "Codigo_ISIN": "Codigo_ISIN",
    "Quantidade_Cotas_Emitidas": "Cotas_Emitidas",
    "Fundo_Exclusivo": "Fundo_Exclusivo",
    "Cotistas_Vinculo_Familiar": "Cotistas_Vinculo_Familiar",
    "Mandato": "Mandato",
    "Segmento_Atuacao": "Segmento_Atuacao",
    "Tipo_Gestao": "Tipo_Gestao",
    "Prazo_Duracao": "Prazo_Duracao",
    "Data_Prazo_Duracao": "Data_Prazo_Duracao",
    "Mercado_Negociacao_Bolsa": "Mercado_Negociacao_Bolsa",
    "Mercado_Negociacao_MBO": "Mercado_Negociacao_MBO",
    "Mercado_Negociacao_MB": "Mercado_Negociacao_MB",
    "Nome_Administrador": "Nome_Administrador",
    "CNPJ_Administrador": "CNPJ_Administrador",
    "Site": "Site",
    "Email": "Email",
}

COLUNAS_COMPLEMENTO = {
    "CNPJ_Fundo": "CNPJ_Fundo",
    "CNPJ_Fundo_Classe": "CNPJ_Fundo",
    "Data_Referencia": "Competencia",
    "Competencia": "Competencia",
    "Data_Informacao_Numero_Cotistas": "Data_Informacao_Numero_Cotistas",
    "Total_Numero_Cotistas": "Numero_Cotistas",
    "Numero_Cotistas_Pessoa_Fisica": "Numero_Cotistas_Pessoa_Fisica",
    "Numero_Cotistas_Pessoa_Juridica_Nao_Financeira": "Numero_Cotistas_Pessoa_Juridica_Nao_Financeira",
    "Numero_Cotistas_Banco_Comercial": "Numero_Cotistas_Banco_Comercial",
    "Numero_Cotistas_Corretora_Distribuidora": "Numero_Cotistas_Corretora_Distribuidora",
    "Numero_Cotistas_Outras_Pessoas_Juridicas_Financeira": "Numero_Cotistas_Outras_Pessoas_Juridicas_Financeira",
    "Numero_Cotistas_Investidores_Nao_Residentes": "Numero_Cotistas_Investidores_Nao_Residentes",
    "Numero_Cotistas_FII": "Numero_Cotistas_FII",
    "Numero_Cotistas_Outros_Fundos": "Numero_Cotistas_Outros_Fundos",
    "Numero_Cotistas_Outros_Tipos": "Numero_Cotistas_Outros_Tipos",
    "Valor_Ativo": "Valor_Ativo",
    "Patrimonio_Liquido": "Patrimonio_Liquido",
    "Cotas_Emitidas": "Cotas_Emitidas",
    "Valor_Patrimonial_Cotas": "Valor_Cota_VPC",
    "Percentual_Despesas_Taxa_Administracao": "Taxa_Administracao",
    "Percentual_Despesas_Agente_Custodiante": "Taxa_Custodiante",
    "Percentual_Rentabilidade_Efetiva_Mes": "Rentabilidade_Efetiva_Mes",
    "Percentual_Rentabilidade_Patrimonial_Mes": "Rentabilidade_Patrimonial_Mes",
    "Percentual_Dividend_Yield_Mes": "Dividend_Yield_Mes",
    "Percentual_Amortizacao_Cotas_Mes": "Amortizacao_Cotas_Mes",
}

COLUNAS_ATIVO = {
    "CNPJ_Fundo": "CNPJ_Fundo",
    "CNPJ_Fundo_Classe": "CNPJ_Fundo",
    "Data_Referencia": "Competencia",
    "Competencia": "Competencia",
    "Total_Necessidades_Liquidez": "Total_Necessidades_Liquidez",
    "Disponibilidades": "Disponibilidades",
    "Titulos_Publicos": "Titulos_Publicos",
    "Titulos_Privados": "Titulos_Privados",
    "Fundos_Renda_Fixa": "Fundos_Renda_Fixa",
    "Total_Investido": "Total_Investido",
    "Direitos_Bens_Imoveis": "Direitos_Bens_Imoveis",
    "Terrenos": "Terrenos",
    "Imoveis_Renda_Acabados": "Imoveis_Renda_Acabados",
    "Imoveis_Renda_Construcao": "Imoveis_Renda_Construcao",
    "Imoveis_Venda_Acabados": "Imoveis_Venda_Acabados",
    "Imoveis_Venda_Construcao": "Imoveis_Venda_Construcao",
    "FII": "Ativo_FII",
    "CRI": "CRI",
    "CRI_CRA": "CRI_CRA",
    "LCI": "LCI",
    "LCI_LCA": "LCI_LCA",
    "LIG": "LIG",
    "Valores_Receber": "Valores_Receber",
    "Contas_Receber_Aluguel": "Contas_Receber_Aluguel",
    "Rendimentos_Distribuir": "Rendimentos_Distribuir",
    "Taxa_Administracao_Pagar": "Taxa_Administracao_Pagar",
    "Taxa_Performance_Pagar": "Taxa_Performance_Pagar",
    "Total_Passivo": "Total_Passivo",
}


def _url_ano(ano: int) -> str:
    return f"{BASE_URL}/inf_mensal_fii_{ano}.zip"


def _ler_csv_do_zip(zip_bytes: bytes, termo: str) -> pd.DataFrame | None:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        alvos = [nome for nome in zf.namelist() if termo in nome.lower() and nome.endswith(".csv")]
        if not alvos:
            return None
        with zf.open(alvos[0]) as arquivo:
            return pd.read_csv(arquivo, sep=";", encoding="latin-1", low_memory=False)


def _normalizar(df: pd.DataFrame | None, mapa: dict[str, str]) -> pd.DataFrame | None:
    if df is None:
        return None

    renomear = {origem: destino for origem, destino in mapa.items() if origem in df.columns}
    df = df.rename(columns=renomear)
    colunas = [col for col in dict.fromkeys(mapa.values()) if col in df.columns]
    return df[colunas].copy()


def baixar_informe_mensal(ano: int | None = None) -> pd.DataFrame | None:
    """Baixa o informe mensal de FIIs e consolida dados gerais e de ativos."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ano = ano or datetime.now().year
    url = _url_ano(ano)
    print(f"Baixando informe mensal CVM ({ano}): {url}")

    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
    except Exception as e:
        print(f"Erro ao baixar informe mensal CVM: {e}")
        return None

    df_geral = _normalizar(_ler_csv_do_zip(resp.content, "geral"), COLUNAS_GERAL)
    df_complemento = _normalizar(_ler_csv_do_zip(resp.content, "complemento"), COLUNAS_COMPLEMENTO)
    df_ativo = _normalizar(_ler_csv_do_zip(resp.content, "ativo"), COLUNAS_ATIVO)

    if df_geral is None and df_complemento is None and df_ativo is None:
        print("Nenhum CSV de informe mensal esperado foi encontrado no ZIP.")
        return None

    if df_complemento is not None:
        df_final = df_complemento.copy()
    elif df_geral is not None:
        df_final = df_geral.copy()
    else:
        df_final = df_ativo.copy()

    for df_extra in [df_geral, df_ativo]:
        if df_extra is None:
            continue
        chaves = [col for col in ["CNPJ_Fundo", "Competencia"] if col in df_final.columns and col in df_extra.columns]
        if chaves:
            colunas_extra = chaves + [col for col in df_extra.columns if col not in chaves and col not in df_final.columns]
            if len(colunas_extra) > len(chaves):
                df_final = df_final.merge(df_extra[colunas_extra], on=chaves, how="left")

    caminho_saida = RAW_DATA_DIR / f"informe_mensal_fii_{ano}.csv"
    df_final.to_csv(caminho_saida, sep=";", index=False, encoding="utf-8")
    print(f"Informe mensal salvo em: {caminho_saida} ({len(df_final)} fundos)")
    return df_final


if __name__ == "__main__":
    baixar_informe_mensal()
