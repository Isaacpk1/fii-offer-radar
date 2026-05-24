from pathlib import Path

import pandas as pd
from bcb import sgs
from langchain.tools import tool


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "src" / "data" / "processed" / "ofertas_fiis_pronto_para_ia.csv"
MACRO_CODES = {
    "selic": 11,
    "ipca": 13522,
    "ipca_12m": 13522,
    "cdi": 12,
    "usd_brl": 1,
    "dolar": 1,
}


def _carregar_base() -> pd.DataFrame:
    return pd.read_csv(CSV_PATH, sep=";", encoding="utf-8")


def obter_macro_atual(indicador: str) -> float:
    chave = indicador.strip().lower()
    if chave not in MACRO_CODES:
        raise ValueError(f"Indicador nao suportado: {indicador}")

    serie = sgs.get({chave: MACRO_CODES[chave]})
    return float(serie.iloc[-1, 0])


@tool
def buscar_macro_atual(indicador: str) -> str:
    """Retorna o valor mais recente de selic, ipca_12m, cdi ou usd_brl."""
    try:
        valor = obter_macro_atual(indicador)
        return f"{indicador.upper()} atual: {valor:.2f}"
    except Exception as e:
        return f"Nao foi possivel buscar o indicador macro: {e}"


@tool
def consultar_oferta_cvm(numero_processo: str) -> str:
    """Consulta uma oferta pelo Numero_Processo da CVM e retorna seus campos principais."""
    try:
        df = _carregar_base()
        filtro = df["Numero_Processo"].astype(str).str.upper() == numero_processo.strip().upper()
        oferta = df[filtro]
        if oferta.empty:
            return f"Nenhuma oferta encontrada para o processo {numero_processo}."
        return oferta.iloc[0].to_json(force_ascii=False)
    except Exception as e:
        return f"Erro ao consultar oferta CVM: {e}"


@tool
def calcular_spread_cdi(taxa_percentual: str) -> str:
    """Calcula o spread, em pontos percentuais, entre uma taxa informada e o CDI atual."""
    try:
        taxa = float(str(taxa_percentual).replace("%", "").replace(",", ".").strip())
        cdi = obter_macro_atual("cdi")
        spread = taxa - cdi
        return f"Taxa informada: {taxa:.2f}%. CDI atual: {cdi:.2f}%. Spread: {spread:.2f} p.p."
    except Exception as e:
        return f"Erro ao calcular spread sobre CDI: {e}"


AGENT_TOOLS = [buscar_macro_atual, consultar_oferta_cvm, calcular_spread_cdi]
