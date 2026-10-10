from __future__ import annotations

import pandas as pd

from database.build_common import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    _ensure_columns,
    _read_csv,
    _to_datetime,
    _to_numeric,
)


def _build_ofertas() -> pd.DataFrame:
    ofertas = _read_csv(PROCESSED_DATA_DIR / "ofertas_fiis_pronto_para_ia.csv")
    bruto = _read_csv(RAW_DATA_DIR / "oferta_resolucao_160_bruto.csv")

    if ofertas.empty:
        return pd.DataFrame()

    if "Qtde_Total_Registrada" not in ofertas.columns and not bruto.empty and "Numero_Processo" in bruto.columns:
        cols = ["Numero_Processo", "Qtde_Total_Registrada"]
        bruto = _ensure_columns(bruto, cols)
        ofertas = ofertas.merge(bruto, on="Numero_Processo", how="left")
    else:
        ofertas["Qtde_Total_Registrada"] = pd.NA

    ofertas = _to_numeric(
        ofertas,
        [
            "Numero_Requerimento",
            "Emissao",
            "Qtde_Total_Registrada",
            "Valor_Total_Registrado",
            "Dias_Ate_Registro",
            "Dias_Ate_Encerramento",
            "Num_Investidores_Mapeados",
            "Qtde_VM_Investidores_Mapeados",
            "Participacao_Pessoa_Natural",
            "Taxa_Selic_Data_Oferta",
            "IPCA_12m_Data_Oferta",
            "CDI_Data_Oferta",
            "USD_BRL_Data_Oferta",
            "Pontos_IFIX_Data_Oferta",
        ],
    )
    ofertas = _to_datetime(
        ofertas,
        [
            "Data_requerimento",
            "Data_Registro",
            "Data_Encerramento",
            "Data_deliberacao_aprovou_oferta",
            "Data_Mudanca_Status",
        ],
    )
    if "Preco_Emissao" not in ofertas.columns:
        ofertas["Preco_Emissao"] = ofertas["Valor_Total_Registrado"] / ofertas["Qtde_Total_Registrada"]
    else:
        ofertas = _to_numeric(ofertas, ["Preco_Emissao"])

    columns = [
        "Numero_Processo",
        "Numero_Requerimento",
        "Rito_Requerimento",
        "CNPJ_Emissor",
        "Nome_Emissor",
        "CNPJ_Lider",
        "Nome_Lider",
        "Grupo_Coordenador",
        "Data_requerimento",
        "Data_Registro",
        "Data_Encerramento",
        "Status_Requerimento",
        "Tipo_requerimento",
        "Tipo_Oferta",
        "Emissao",
        "Publico_alvo",
        "Bookbuilding",
        "Tem_Bookbuilding",
        "Oferta_inicial",
        "Oferta_vasos_comunicantes",
        "Destinacao_recursos",
        "Data_deliberacao_aprovou_oferta",
        "Mercado_negociacao",
        "Regime_distribuicao",
        "Administrador",
        "Gestor",
        "Escriturador",
        "Custodiante",
        "Qtde_Total_Registrada",
        "Valor_Total_Registrado",
        "Preco_Emissao",
        "Dias_Ate_Registro",
        "Dias_Ate_Encerramento",
        "Oferta_Encerrada",
        "Num_Investidores_Mapeados",
        "Qtde_VM_Investidores_Mapeados",
        "Participacao_Pessoa_Natural",
        "Taxa_Selic_Data_Oferta",
        "IPCA_12m_Data_Oferta",
        "CDI_Data_Oferta",
        "USD_BRL_Data_Oferta",
        "Pontos_IFIX_Data_Oferta",
        "Status_Anterior",
        "Data_Mudanca_Status",
    ]
    ofertas = _ensure_columns(ofertas, columns)
    ofertas.columns = [
        "numero_processo",
        "numero_requerimento",
        "rito_requerimento",
        "cnpj_emissor",
        "nome_emissor",
        "cnpj_lider",
        "nome_lider",
        "grupo_coordenador",
        "data_requerimento",
        "data_registro",
        "data_encerramento",
        "status_requerimento",
        "tipo_requerimento",
        "tipo_oferta",
        "emissao",
        "publico_alvo",
        "bookbuilding",
        "tem_bookbuilding",
        "oferta_inicial",
        "oferta_vasos_comunicantes",
        "destinacao_recursos",
        "data_deliberacao_aprovou_oferta",
        "mercado_negociacao",
        "regime_distribuicao",
        "administrador",
        "gestor",
        "escriturador",
        "custodiante",
        "quantidade_registrada",
        "valor_total_registrado",
        "preco_emissao",
        "dias_ate_registro",
        "dias_ate_encerramento",
        "oferta_encerrada",
        "num_investidores_mapeados",
        "quantidade_vm_investidores_mapeados",
        "participacao_pessoa_natural",
        "taxa_selic_data_oferta",
        "ipca_12m_data_oferta",
        "cdi_data_oferta",
        "usd_brl_data_oferta",
        "pontos_ifix_data_oferta",
        "status_anterior",
        "data_mudanca_status",
    ]
    return ofertas.drop_duplicates("numero_processo", keep="last")


