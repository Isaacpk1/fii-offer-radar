from pathlib import Path

import pandas as pd

try:
    from data_processing.utils import para_numero
except ModuleNotFoundError:
    from utils import para_numero


SRC_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = SRC_DIR / "data" / "raw"

COLUNAS_OFERTA_FII = [
    "Numero_Requerimento",
    "Rito_Requerimento",
    "Numero_Processo",
    "Data_requerimento",
    "Data_Registro",
    "Data_Encerramento",
    "Status_Requerimento",
    "Valor_Mobiliario",
    "Tipo_requerimento",
    "Bookbuilding",
    "CNPJ_Emissor",
    "Nome_Emissor",
    "CNPJ_Lider",
    "Nome_Lider",
    "Grupo_Coordenador",
    "Tipo_Oferta",
    "Emissao",
    "Qtde_Total_Registrada",
    "Valor_Total_Registrado",
    "Oferta_inicial",
    "Oferta_vasos_comunicantes",
    "Publico_alvo",
    "Destinacao_recursos",
    "Data_deliberacao_aprovou_oferta",
    "Mercado_negociacao",
    "Regime_distribuicao",
    "Administrador",
    "Gestor",
    "Escriturador",
    "Custodiante",
    "Num_Invest_Pessoa_Natural",
    "Qtde_VM_Pessoa_Natural",
    "Num_Invest_Fundos_Investimento",
    "Qtde_VM_Fundos_Investimento",
    "Num_Invest_Investidor_Estrangeiro",
    "Qtde_VM_Investidor_Estrangeiro",
    "Num_Invest_Demais_Pessoa_Juridica",
    "Qtde_VM_Demais_Pessoa_Juridica",
]

COLUNAS_DATA = [
    "Data_requerimento",
    "Data_Registro",
    "Data_Encerramento",
    "Data_deliberacao_aprovou_oferta",
]

COLUNAS_NUMERICAS = [
    "Numero_Requerimento",
    "Emissao",
    "Qtde_Total_Registrada",
    "Valor_Total_Registrado",
    "Num_Invest_Pessoa_Natural",
    "Qtde_VM_Pessoa_Natural",
    "Num_Invest_Fundos_Investimento",
    "Qtde_VM_Fundos_Investimento",
    "Num_Invest_Investidor_Estrangeiro",
    "Qtde_VM_Investidor_Estrangeiro",
    "Num_Invest_Demais_Pessoa_Juridica",
    "Qtde_VM_Demais_Pessoa_Juridica",
]


MAPA_LAYOUT_ATUAL_CVM = {
    "Rito_Oferta": "Rito_Requerimento",
    "Data_Abertura_Processo": "Data_requerimento",
    "Data_Registro_Oferta": "Data_Registro",
    "Data_Encerramento_Oferta": "Data_Encerramento",
    "Tipo_Ativo": "Valor_Mobiliario",
    "Modalidade_Oferta": "Tipo_requerimento",
    "Quantidade_Total": "Qtde_Total_Registrada",
    "Valor_Total": "Valor_Total_Registrado",
    "Oferta_Inicial": "Oferta_inicial",
    "Nr_Pessoa_Fisica": "Num_Invest_Pessoa_Natural",
    "Qtd_Pessoa_Fisica": "Qtde_VM_Pessoa_Natural",
    "Nr_Fundos_Investimento": "Num_Invest_Fundos_Investimento",
    "Qtd_Fundos_Investimento": "Qtde_VM_Fundos_Investimento",
    "Nr_Investidor_Estrangeiro": "Num_Invest_Investidor_Estrangeiro",
    "Qtd_Investidor_Estrangeiro": "Qtde_VM_Investidor_Estrangeiro",
    "Nr_Demais_Pessoa_Juridica": "Num_Invest_Demais_Pessoa_Juridica",
    "Qtd_Demais_Pessoa_Juridica": "Qtde_VM_Demais_Pessoa_Juridica",
}


def _normalizar_layout_cvm(df: pd.DataFrame) -> pd.DataFrame:
    """Adapta layouts diferentes do arquivo de ofertas CVM para o schema interno."""
    normalizado = df.copy()
    for origem, destino in MAPA_LAYOUT_ATUAL_CVM.items():
        if destino not in normalizado.columns and origem in normalizado.columns:
            normalizado[destino] = normalizado[origem]

    if "Status_Requerimento" not in normalizado.columns:
        status = pd.Series(pd.NA, index=normalizado.index, dtype="object")
        if "Ultimo_Comunicado" in normalizado.columns:
            status = status.fillna(normalizado["Ultimo_Comunicado"])
        if "Modalidade_Registro" in normalizado.columns:
            status = status.fillna(normalizado["Modalidade_Registro"])
        if "Modalidade_Oferta" in normalizado.columns:
            status = status.fillna(normalizado["Modalidade_Oferta"])
        normalizado["Status_Requerimento"] = status

    if "Bookbuilding" not in normalizado.columns:
        normalizado["Bookbuilding"] = pd.NA
    if "Oferta_vasos_comunicantes" not in normalizado.columns:
        normalizado["Oferta_vasos_comunicantes"] = pd.NA

    return normalizado


def _filtrar_ofertas_fii(df: pd.DataFrame) -> pd.DataFrame:
    if "Valor_Mobiliario" in df.columns:
        valor_mobiliario = df["Valor_Mobiliario"].astype(str)
        mask_valor = valor_mobiliario.str.contains(
            r"Cotas de FII|QUOTAS DE FUNDO IMOBILI|COTAS DE FUNDO IMOBILI",
            case=False,
            na=False,
            regex=True,
        )
    else:
        mask_valor = pd.Series(False, index=df.index)

    if "Tipo_Fundo_Investimento" in df.columns:
        tipo_fundo = df["Tipo_Fundo_Investimento"].astype(str)
        mask_tipo_fundo = tipo_fundo.str.contains(
            r"FII|Fundo de Investimento Imobili",
            case=False,
            na=False,
            regex=True,
        )
    else:
        mask_tipo_fundo = pd.Series(False, index=df.index)

    return df[mask_valor | mask_tipo_fundo].copy()


def _filtrar_ofertas_primarias(df: pd.DataFrame) -> pd.DataFrame:
    if "Tipo_Oferta" not in df.columns:
        return df

    tipo_oferta = df["Tipo_Oferta"].astype(str)
    return df[tipo_oferta.str.contains("prim", case=False, na=False)].copy()


def limpar_dados_cvm():
    """Le os dados brutos da CVM, filtra FIIs e formata as colunas."""
    caminho_bruto = RAW_DATA_DIR / "oferta_resolucao_160_bruto.csv"
    print(f"Limpando dados da CVM a partir de: {caminho_bruto}")

    try:
        df = pd.read_csv(caminho_bruto, sep=";", encoding="utf-8", low_memory=False)
        df = _normalizar_layout_cvm(df)
        df_fiis = _filtrar_ofertas_fii(df)
        df_fiis = _filtrar_ofertas_primarias(df_fiis)

        colunas_existentes = [col for col in COLUNAS_OFERTA_FII if col in df_fiis.columns]
        df_limpo = df_fiis[colunas_existentes].copy()

        for coluna in COLUNAS_DATA:
            if coluna in df_limpo.columns:
                df_limpo[coluna] = pd.to_datetime(df_limpo[coluna], errors="coerce")

        for coluna in COLUNAS_NUMERICAS:
            if coluna in df_limpo.columns:
                df_limpo[coluna] = para_numero(df_limpo[coluna])

        if "Data_requerimento" in df_limpo.columns:
            df_limpo = df_limpo.dropna(subset=["Data_requerimento"])
            df_limpo = df_limpo.sort_values(by="Data_requerimento", ascending=False)

        print(f"Limpeza concluida: {len(df_limpo)} ofertas de FIIs prontas para cruzamento.")
        return df_limpo

    except Exception as e:
        print(f"Erro ao limpar dados da CVM: {e}")
        return None
