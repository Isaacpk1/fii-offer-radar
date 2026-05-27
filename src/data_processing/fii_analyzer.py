from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from data_processing.utils import para_numero
except ModuleNotFoundError:
    from utils import para_numero


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "src" / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "src" / "data" / "processed"


def _primeira_coluna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    normalizadas = {col.lower(): col for col in df.columns}
    for candidato in candidatos:
        coluna = normalizadas.get(candidato.lower())
        if coluna:
            return coluna
    return None


def _garantir_coluna(df: pd.DataFrame, destino: str, candidatos: list[str]) -> None:
    if destino in df.columns:
        return
    coluna = _primeira_coluna(df, candidatos)
    df[destino] = df[coluna] if coluna else np.nan


def _carregar_informe(ano: int) -> pd.DataFrame | None:
    caminho = RAW_DATA_DIR / f"informe_mensal_fii_{ano}.csv"
    if not caminho.exists():
        print(f"Informe mensal nao encontrado: {caminho}")
        return None

    df = pd.read_csv(caminho, sep=";", encoding="utf-8", low_memory=False)
    _garantir_coluna(df, "CNPJ_Fundo", ["CNPJ_Fundo", "CNPJ_Fundo_Classe"])
    _garantir_coluna(df, "Competencia", ["Competencia", "Data_Referencia"])
    _garantir_coluna(df, "Valor_Cota_VPC", ["Valor_Cota_VPC", "Valor_Patrimonial_Cotas", "VL_Cota", "Valor_Cota"])
    _garantir_coluna(df, "Patrimonio_Liquido", ["Patrimonio_Liquido", "VL_Patrim_Liq", "PL_Total"])
    _garantir_coluna(df, "Numero_Cotistas", ["Numero_Cotistas", "Total_Numero_Cotistas", "NR_Cotst"])

    for coluna in [
        "Valor_Cota_VPC",
        "Patrimonio_Liquido",
        "Numero_Cotistas",
        "Taxa_Administracao",
        "Taxa_Custodiante",
        "Dividend_Yield_Mes",
        "Rentabilidade_Patrimonial_Mes",
        "Disponibilidades",
        "Total_Passivo",
        "Direitos_Bens_Imoveis",
        "Imoveis_Renda_Acabados",
        "Imoveis_Renda_Construcao",
        "Imoveis_Venda_Acabados",
        "Imoveis_Venda_Construcao",
        "Ativo_FII",
        "CRI",
        "CRI_CRA",
        "LCI",
        "LCI_LCA",
        "LIG",
    ]:
        if coluna in df.columns:
            df[coluna] = para_numero(df[coluna])

    if "Competencia" in df.columns:
        df["Competencia"] = pd.to_datetime(df["Competencia"], errors="coerce")
        df = df.sort_values("Competencia").drop_duplicates(subset="CNPJ_Fundo", keep="last")

    pl = df["Patrimonio_Liquido"].where(df["Patrimonio_Liquido"] > 0) if "Patrimonio_Liquido" in df.columns else np.nan
    if "Disponibilidades" in df.columns:
        df["Caixa_Sobre_PL"] = df["Disponibilidades"] / pl
    colunas_imoveis = [
        col for col in [
            "Direitos_Bens_Imoveis",
            "Imoveis_Renda_Acabados",
            "Imoveis_Renda_Construcao",
            "Imoveis_Venda_Acabados",
            "Imoveis_Venda_Construcao",
        ] if col in df.columns
    ]
    if colunas_imoveis:
        df["Imoveis_Sobre_PL"] = df[colunas_imoveis].sum(axis=1, min_count=1) / pl
    colunas_cri = [col for col in ["CRI", "CRI_CRA"] if col in df.columns]
    if colunas_cri:
        df["CRI_Sobre_PL"] = df[colunas_cri].sum(axis=1, min_count=1) / pl
    if "Ativo_FII" in df.columns:
        df["FII_Sobre_PL"] = df["Ativo_FII"] / pl
    if "Total_Passivo" in df.columns:
        df["Passivo_Sobre_PL"] = df["Total_Passivo"] / pl

    return df


def _carregar_mercado() -> pd.DataFrame:
    caminho = RAW_DATA_DIR / "fii_mercado_bruto.csv"
    colunas = ["CNPJ_Emissor", "Ticker", "Preco_Cota", "Volume_Medio_Diario"]
    if not caminho.exists():
        return pd.DataFrame(columns=colunas)

    df = pd.read_csv(caminho, sep=";", encoding="utf-8")
    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = np.nan
    for coluna in ["Preco_Cota", "Volume_Medio_Diario"]:
        df[coluna] = para_numero(df[coluna])
    return df[colunas].drop_duplicates(subset="CNPJ_Emissor", keep="last")


def _carregar_historico_ofertas() -> pd.DataFrame:
    caminho = RAW_DATA_DIR / "oferta_resolucao_160_bruto.csv"
    colunas_saida = [
        "CNPJ_Emissor",
        "Preco_Emissao",
        "Total_Emissoes",
        "Volume_Total_Ofertas",
        "Coordenador_Principal",
    ]
    if not caminho.exists():
        return pd.DataFrame(columns=colunas_saida)

    df = pd.read_csv(caminho, sep=";", encoding="utf-8", low_memory=False)
    if "Valor_Mobiliario" in df.columns:
        df = df[df["Valor_Mobiliario"] == "Cotas de FII"].copy()
    if "CNPJ_Emissor" not in df.columns:
        return pd.DataFrame(columns=colunas_saida)

    for coluna in ["Valor_Total_Registrado", "Qtde_Total_Registrada"]:
        if coluna in df.columns:
            df[coluna] = para_numero(df[coluna])
        else:
            df[coluna] = np.nan

    df["Preco_Emissao"] = np.where(
        df["Qtde_Total_Registrada"] > 0,
        df["Valor_Total_Registrado"] / df["Qtde_Total_Registrada"],
        np.nan,
    )

    if "Data_requerimento" in df.columns:
        df["Data_requerimento"] = pd.to_datetime(df["Data_requerimento"], errors="coerce")
        recentes = df.sort_values("Data_requerimento").drop_duplicates("CNPJ_Emissor", keep="last")
    else:
        recentes = df.drop_duplicates("CNPJ_Emissor", keep="last")

    resumo = (
        df.groupby("CNPJ_Emissor", as_index=False)
        .agg(
            Total_Emissoes=("CNPJ_Emissor", "size"),
            Volume_Total_Ofertas=("Valor_Total_Registrado", "sum"),
        )
    )

    if "Nome_Lider" in df.columns:
        lideres = (
            df.groupby(["CNPJ_Emissor", "Nome_Lider"], as_index=False)
            .agg(Volume_Lider=("Valor_Total_Registrado", "sum"))
            .sort_values(["CNPJ_Emissor", "Volume_Lider"], ascending=[True, False])
            .drop_duplicates("CNPJ_Emissor")
            .rename(columns={"Nome_Lider": "Coordenador_Principal"})
        )
        resumo = resumo.merge(lideres[["CNPJ_Emissor", "Coordenador_Principal"]], on="CNPJ_Emissor", how="left")
    else:
        resumo["Coordenador_Principal"] = np.nan

    return recentes[["CNPJ_Emissor", "Preco_Emissao"]].merge(resumo, on="CNPJ_Emissor", how="left")


def consolidar_analise_fiis(ano_informe: int | None = None) -> pd.DataFrame | None:
    """Consolida informe mensal, mercado e historico de ofertas em uma base analitica."""
    ano = ano_informe or datetime.now().year
    df_analise = _carregar_informe(ano)
    if df_analise is None:
        return None

    df_analise = df_analise.merge(
        _carregar_mercado(),
        left_on="CNPJ_Fundo",
        right_on="CNPJ_Emissor",
        how="left",
    ).drop(columns=["CNPJ_Emissor"], errors="ignore")

    df_analise = df_analise.merge(
        _carregar_historico_ofertas(),
        left_on="CNPJ_Fundo",
        right_on="CNPJ_Emissor",
        how="left",
    ).drop(columns=["CNPJ_Emissor"], errors="ignore")

    df_analise["P_VP"] = np.where(
        df_analise["Valor_Cota_VPC"] > 0,
        (df_analise["Preco_Cota"] / df_analise["Valor_Cota_VPC"]).round(2),
        np.nan,
    )
    df_analise["P_VP_Emissao"] = np.where(
        (df_analise["Preco_Emissao"] > 0) & (df_analise["Valor_Cota_VPC"] > 0),
        (df_analise["Preco_Emissao"] / df_analise["Valor_Cota_VPC"]).round(2),
        np.nan,
    )
    df_analise["Desconto_Oferta_VP"] = np.where(
        (df_analise["Preco_Emissao"] > 0) & (df_analise["Valor_Cota_VPC"] > 0),
        (df_analise["Preco_Emissao"] / df_analise["Valor_Cota_VPC"] - 1).round(4),
        np.nan,
    )

    condicoes = [
        df_analise["Preco_Cota"].isna() | df_analise["Preco_Emissao"].isna(),
        df_analise["Preco_Emissao"] < df_analise["Preco_Cota"],
        df_analise["Preco_Emissao"] > df_analise["Preco_Cota"],
    ]
    df_analise["Status_Viabilidade_Oferta"] = np.select(
        condicoes,
        ["Aguardando cotacao/dados", "Oferta abaixo do mercado", "Melhor comprar na B3"],
        default="Precos equivalentes",
    )

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    caminho_final = PROCESSED_DATA_DIR / "fii_analise_completa.csv"
    df_analise.to_csv(caminho_final, sep=";", index=False, encoding="utf-8")
    print(f"Analise de FIIs salva em: {caminho_final} ({len(df_analise)} fundos)")
    return df_analise


if __name__ == "__main__":
    consolidar_analise_fiis()
