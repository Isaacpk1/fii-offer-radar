import pandas as pd
import pytest

from data_processing.confidence_scorer import (
    _classificar_sinal,
    calcular_confianca,
    enriquecer_dataframe_com_confianca,
)


def _oferta_completa() -> pd.Series:
    return pd.Series(
        {
            "preco_emissao": 98.0,
            "valor_cota_vpc": 100.0,
            "preco_cota_b3": 101.0,
            "volume_medio_diario": 2_500_000,
            "p_vp_emissao": 0.98,
            "sinal_preco_b3": "Emissao abaixo da B3",
            "sinal_preco_vp": "Desconto sobre VP",
            "sinal_liquidez": "Liquidez forte",
            "sinal_historico": "Emissor recorrente",
            "total_emissoes": 6,
            "taxa_selic_data_oferta": 10.5,
        }
    )


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Emissao abaixo da B3", "positivo"),
        ("Premio sobre VP", "negativo"),
        ("Sem preco B3", "ausente"),
        ("nao informado", "ausente"),
        (None, "ausente"),
        ("texto desconhecido", "ausente"),
    ],
)
def test_classificar_sinal(texto, esperado):
    assert _classificar_sinal(texto) == esperado


def test_oferta_completa_tem_confianca_alta():
    resultado = calcular_confianca(_oferta_completa())

    assert resultado.score_dados == 40
    assert resultado.score_sinais == 35
    assert resultado.score_contexto == 25
    assert resultado.score_total == 100
    assert resultado.nivel == "Alta"
    assert resultado.dados_ausentes == []
    assert "todos os dados criticos presentes" in resultado.resumo_auditavel


def test_oferta_vazia_e_insuficiente():
    resultado = calcular_confianca(pd.Series(dtype="object"))

    assert resultado.score_total == 0
    assert resultado.nivel == "Insuficiente"
    assert set(resultado.dados_ausentes) == {
        "preco_emissao",
        "valor_cota_vpc",
        "preco_cota_b3",
        "volume_medio_diario",
        "p_vp_emissao",
    }


def test_sinais_conflitantes_reduzem_score():
    oferta = _oferta_completa()
    oferta["sinal_preco_vp"] = "Premio sobre VP"
    oferta["sinal_liquidez"] = "Liquidez baixa"

    resultado = calcular_confianca(oferta)

    assert resultado.score_sinais < 35
    assert resultado.sinais_conflitantes


def test_enriquecer_dataframe_adiciona_colunas():
    df = pd.DataFrame([_oferta_completa(), pd.Series(dtype="object")])

    enriquecido = enriquecer_dataframe_com_confianca(df)

    assert list(enriquecido["confianca_nivel"]) == ["Alta", "Insuficiente"]
    assert "dados_ausentes_criticos" in enriquecido.columns
    assert "confianca_total" not in df.columns


def test_enriquecer_dataframe_vazio_retorna_vazio():
    vazio = pd.DataFrame()
    assert enriquecer_dataframe_com_confianca(vazio).empty
