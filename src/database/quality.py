from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from database.build_common import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    _coalesce_duplicate_columns,
    _ensure_columns,
    _normalizar_yield_mensal,
    _read_csv,
    _to_datetime,
    _to_numeric,
)
from data_processing.confidence_scorer import enriquecer_dataframe_com_confianca


def _build_quality_report(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    now = datetime.now()
    for table, df in tables.items():
        total = len(df)
        if total == 0:
            rows.append(
                {
                    "tabela": table,
                    "coluna": "*",
                    "total_linhas": 0,
                    "valores_preenchidos": 0,
                    "cobertura_percentual": 0.0,
                    "observacao": "Tabela vazia; fonte ainda nao integrada ou arquivo ausente.",
                    "gerado_em": now,
                }
            )
            continue

        for column in df.columns:
            filled = int(df[column].notna().sum())
            coverage = round(filled / total * 100, 2)
            observation = "OK" if coverage > 0 else "Sem cobertura nos dados atuais."
            rows.append(
                {
                    "tabela": table,
                    "coluna": column,
                    "total_linhas": total,
                    "valores_preenchidos": filled,
                    "cobertura_percentual": coverage,
                    "observacao": observation,
                    "gerado_em": now,
                }
            )
    return pd.DataFrame(rows)


