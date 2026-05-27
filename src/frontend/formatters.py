import pandas as pd

from frontend.config import AMBER, GREEN, RED


def formatar_moeda(valor: float | int | None) -> str:
    if pd.isna(valor):
        return "N/D"
    valor = float(valor)
    if abs(valor) >= 1_000_000_000:
        return f"R$ {valor / 1_000_000_000:.2f} bi"
    if abs(valor) >= 1_000_000:
        return f"R$ {valor / 1_000_000:.2f} mi"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_percentual(valor: float | int | None, escala_decimal: bool = False) -> str:
    if pd.isna(valor):
        return "N/D"
    numero = float(valor) * 100 if escala_decimal else float(valor)
    return f"{numero:.2f}%"


def status_class(status: str) -> str:
    if status == "Implementado":
        return "status-ok"
    if status == "Parcial":
        return "status-mid"
    return "status-empty"


def coverage_color(value: float) -> str:
    if value >= 80:
        return GREEN
    if value >= 30:
        return AMBER
    return RED
