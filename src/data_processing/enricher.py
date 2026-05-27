import json
from pathlib import Path

import pandas as pd

try:
    from data_processing.utils import para_numero
except ModuleNotFoundError:
    from utils import para_numero


SRC_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = SRC_DIR / "data" / "raw"
PROCESSED_DATA_DIR = SRC_DIR / "data" / "processed"
ALERTS_PATH = PROCESSED_DATA_DIR / "status_monitor_alerts.json"
COLUNAS_MACRO = [
    "Taxa_Selic_Data_Oferta",
    "IPCA_12m_Data_Oferta",
    "CDI_Data_Oferta",
    "USD_BRL_Data_Oferta",
]


def _carregar_macro() -> pd.DataFrame:
    caminho_macro = RAW_DATA_DIR / "macro_bcb_bruto.csv"
    if caminho_macro.exists():
        df_macro = pd.read_csv(caminho_macro, sep=";")
        df_macro["data"] = pd.to_datetime(df_macro["data"], errors="coerce")
    else:
        df_selic = pd.read_csv(RAW_DATA_DIR / "selic_bruto.csv", sep=";")
        df_selic["data"] = pd.to_datetime(df_selic["data"], errors="coerce")
        df_macro = df_selic.rename(columns={"valor": "Taxa_Selic_Data_Oferta"})

    for coluna in COLUNAS_MACRO:
        if coluna in df_macro.columns:
            df_macro[coluna] = para_numero(df_macro[coluna])

    df_macro = df_macro.dropna(subset=["data"]).sort_values("data")
    colunas_existentes = [c for c in COLUNAS_MACRO if c in df_macro.columns]
    df_macro[colunas_existentes] = df_macro[colunas_existentes].ffill()
    return df_macro


def _carregar_ifix() -> pd.DataFrame:
    caminho_ifix = RAW_DATA_DIR / "ifix_bruto.csv"
    if not caminho_ifix.exists():
        return pd.DataFrame(columns=["Date", "Close"])

    df_ifix = pd.read_csv(caminho_ifix, sep=";")
    if "Date" not in df_ifix.columns or "Close" not in df_ifix.columns:
        return pd.DataFrame(columns=["Date", "Close"])

    df_ifix["Date"] = pd.to_datetime(df_ifix["Date"], errors="coerce", utc=True).dt.tz_localize(None)
    df_ifix["Close"] = para_numero(df_ifix["Close"])
    return df_ifix.dropna(subset=["Date", "Close"]).sort_values("Date")


def _adicionar_metricas_oferta(df: pd.DataFrame) -> pd.DataFrame:
    if {"Valor_Total_Registrado", "Qtde_Total_Registrada"}.issubset(df.columns):
        valor = para_numero(df["Valor_Total_Registrado"])
        quantidade = para_numero(df["Qtde_Total_Registrada"])
        df["Preco_Emissao"] = valor / quantidade.where(quantidade > 0)

    pares_datas = {
        "Dias_Ate_Registro": ("Data_requerimento", "Data_Registro"),
        "Dias_Ate_Encerramento": ("Data_requerimento", "Data_Encerramento"),
    }
    for destino, (inicio, fim) in pares_datas.items():
        if inicio in df.columns and fim in df.columns:
            df[destino] = (df[fim] - df[inicio]).dt.days

    if "Status_Requerimento" in df.columns:
        df["Oferta_Encerrada"] = df["Status_Requerimento"].astype(str).str.upper().eq("OFERTA ENCERRADA")
    if "Bookbuilding" in df.columns:
        df["Tem_Bookbuilding"] = df["Bookbuilding"].astype(str).str.upper().eq("S")

    quantidade_cols = [col for col in df.columns if col.startswith("Qtde_VM_")]
    investidor_cols = [col for col in df.columns if col.startswith("Num_Invest_")]
    if quantidade_cols:
        df["Qtde_VM_Investidores_Mapeados"] = df[quantidade_cols].apply(para_numero).sum(axis=1)
    if investidor_cols:
        df["Num_Investidores_Mapeados"] = df[investidor_cols].apply(para_numero).sum(axis=1)

    if {"Qtde_VM_Pessoa_Natural", "Qtde_VM_Investidores_Mapeados"}.issubset(df.columns):
        total = para_numero(df["Qtde_VM_Investidores_Mapeados"])
        pessoa_fisica = para_numero(df["Qtde_VM_Pessoa_Natural"])
        df["Participacao_Pessoa_Natural"] = pessoa_fisica / total.where(total > 0)

    return df


def cruzar_cvm_com_macro(df_cvm_limpo):
    """Cruza os dados limpos da CVM com indicadores macro e IFIX."""
    print("Enriquecendo ofertas com dados macroeconomicos e IFIX...")

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        df_macro = _carregar_macro()
        df_ifix = _carregar_ifix()

        df_cvm_limpo = df_cvm_limpo.sort_values("Data_requerimento")
        df_macro = df_macro.sort_values("data")

        df_enriquecido = pd.merge_asof(
            df_cvm_limpo,
            df_macro,
            left_on="Data_requerimento",
            right_on="data",
            direction="backward",
        )
        df_enriquecido.drop(columns=["data"], inplace=True)

        if not df_ifix.empty:
            df_enriquecido = pd.merge_asof(
                df_enriquecido,
                df_ifix[["Date", "Close"]],
                left_on="Data_requerimento",
                right_on="Date",
                direction="backward",
            )
            df_enriquecido.rename(columns={"Close": "Pontos_IFIX_Data_Oferta"}, inplace=True)
            df_enriquecido.drop(columns=["Date"], inplace=True)
        else:
            df_enriquecido["Pontos_IFIX_Data_Oferta"] = pd.NA

        df_enriquecido = _adicionar_metricas_oferta(df_enriquecido)

        colunas_arredondar = [
            "Taxa_Selic_Data_Oferta",
            "IPCA_12m_Data_Oferta",
            "CDI_Data_Oferta",
            "USD_BRL_Data_Oferta",
            "Pontos_IFIX_Data_Oferta",
        ]
        for coluna in colunas_arredondar:
            if coluna in df_enriquecido.columns:
                df_enriquecido[coluna] = df_enriquecido[coluna].round(2)

        # Cruza historico de mudancas de status do monitor
        df_enriquecido = enriquecer_com_historico_status(df_enriquecido)

        df_enriquecido = df_enriquecido.sort_values(
            by="Data_requerimento",
            ascending=False,
        )

        caminho_final = PROCESSED_DATA_DIR / "ofertas_fiis_pronto_para_ia.csv"
        df_enriquecido.to_csv(caminho_final, sep=";", index=False, encoding="utf-8")

        print(f"Enriquecimento concluido. Arquivo final salvo em: {caminho_final}")
        return df_enriquecido

    except Exception as e:
        print(f"Erro ao cruzar dados: {e}")
        return None


def enriquecer_com_historico_status(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona colunas de historico de mudanca de status lidas do monitor."""
    if not ALERTS_PATH.exists():
        df["Status_Anterior"] = None
        df["Data_Mudanca_Status"] = None
        return df

    try:
        alertas = json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
        if not alertas:
            df["Status_Anterior"] = None
            df["Data_Mudanca_Status"] = None
            return df

        df_alertas = pd.DataFrame(alertas)[
            ["Numero_Processo", "Status_Anterior", "Detectado_Em"]
        ].rename(columns={"Detectado_Em": "Data_Mudanca_Status"})

        # Mantem apenas a mudanca mais recente por processo
        df_alertas = df_alertas.sort_values("Data_Mudanca_Status").drop_duplicates(
            subset="Numero_Processo", keep="last"
        )

        df = df.merge(
            df_alertas,
            on="Numero_Processo",
            how="left",
        )
        print(f"Historico de status cruzado: {df['Status_Anterior'].notna().sum()} oferta(s) com mudanca registrada.")

    except Exception as e:
        print(f"Aviso: nao foi possivel cruzar historico de status: {e}")
        df["Status_Anterior"] = None
        df["Data_Mudanca_Status"] = None

    return df
