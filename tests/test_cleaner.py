import pandas as pd

from data_processing.cleaner import (
    _filtrar_ofertas_fii,
    _filtrar_ofertas_primarias,
    _normalizar_layout_cvm,
)
from data_processing.utils import para_numero


def test_para_numero_entende_formato_brasileiro():
    serie = pd.Series(["1.234,56", "10", "abc", "0,5"])
    resultado = para_numero(serie)

    assert resultado.iloc[0] == 1234.56
    assert resultado.iloc[1] == 10
    assert pd.isna(resultado.iloc[2])
    assert resultado.iloc[3] == 0.5


def test_normalizar_layout_novo_da_cvm():
    df = pd.DataFrame(
        {
            "Tipo_Ativo": ["Cotas de FII"],
            "Valor_Total": ["1000"],
            "Ultimo_Comunicado": ["Oferta Encerrada"],
        }
    )

    normalizado = _normalizar_layout_cvm(df)

    assert normalizado.loc[0, "Valor_Mobiliario"] == "Cotas de FII"
    assert normalizado.loc[0, "Valor_Total_Registrado"] == "1000"
    assert normalizado.loc[0, "Status_Requerimento"] == "Oferta Encerrada"
    assert "Bookbuilding" in normalizado.columns


def test_filtrar_ofertas_fii():
    df = pd.DataFrame(
        {
            "Valor_Mobiliario": ["Cotas de FII", "Debentures", "QUOTAS DE FUNDO IMOBILIARIO"],
        }
    )

    assert len(_filtrar_ofertas_fii(df)) == 2


def test_filtrar_ofertas_primarias():
    df = pd.DataFrame({"Tipo_Oferta": ["Primaria", "Secundaria", "PRIMÁRIA"]})

    assert len(_filtrar_ofertas_primarias(df)) == 2
