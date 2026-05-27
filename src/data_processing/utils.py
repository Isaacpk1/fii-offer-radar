import pandas as pd


def para_numero(serie: pd.Series) -> pd.Series:
    texto = serie.astype(str).str.strip()
    texto = texto.mask(
        texto.str.contains(",", regex=False),
        texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    return pd.to_numeric(texto, errors="coerce")
