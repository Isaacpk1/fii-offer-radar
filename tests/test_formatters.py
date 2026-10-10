import pytest

from frontend.formatters import formatar_moeda, formatar_percentual


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (None, "N/D"),
        (2_500_000_000, "R$ 2,50 bi"),
        (3_200_000, "R$ 3,20 mi"),
        (1234.5, "R$ 1.234,50"),
    ],
)
def test_formatar_moeda(valor, esperado):
    assert formatar_moeda(valor) == esperado


def test_formatar_percentual():
    assert formatar_percentual(None) == "N/D"
    assert formatar_percentual(12.345) == "12.35%"
    assert formatar_percentual(0.1, escala_decimal=True) == "10.00%"
