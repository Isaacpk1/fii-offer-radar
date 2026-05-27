from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd
import requests

from data_extraction.oferta_document_common import CVM_DOCS_DIR, CVM_DOCS_URL, CVM_TIPOS_RELEVANTES, USER_AGENT, _normalizar_texto
from data_extraction.oferta_document_search import _classificar_documento


def _anos_para_documentos(manifest: pd.DataFrame) -> list[int]:
    datas = pd.to_datetime(manifest.get("data_requerimento"), errors="coerce")
    anos = set(datas.dropna().dt.year.astype(int).tolist())
    ano_atual = datetime.now().year
    anos.add(ano_atual)
    anos.update({ano_atual - 1, ano_atual - 2})
    return sorted(ano for ano in anos if ano >= 2021)


def _normalizar_tipo_cvm(tipo: str | None) -> str | None:
    texto = _normalizar_texto(tipo).upper()
    texto_ascii = (
        texto.replace("Á", "A")
        .replace("Â", "A")
        .replace("Ã", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
    )
    return CVM_TIPOS_RELEVANTES.get(texto) or CVM_TIPOS_RELEVANTES.get(texto_ascii)


def _carregar_documentos_cvm(anos: list[int]) -> pd.DataFrame:
    CVM_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for ano in anos:
        cache_path = CVM_DOCS_DIR / f"eventual_fi_{ano}.csv"
        if cache_path.exists():
            df = pd.read_csv(cache_path, sep=";", encoding="latin1", low_memory=False)
        else:
            try:
                df = pd.read_csv(CVM_DOCS_URL.format(ano=ano), sep=";", encoding="latin1", low_memory=False)
            except Exception:
                continue
            df.to_csv(cache_path, sep=";", index=False, encoding="latin1")
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    docs = pd.concat(frames, ignore_index=True)
    docs = docs.rename(
        columns={
            "CNPJ_FUNDO_CLASSE": "cnpj_emissor",
            "DENOM_SOCIAL": "nome_emissor",
            "DT_COMPTC": "data_documento",
            "DT_RECEB": "data_recebimento",
            "TP_DOC": "tipo_cvm",
            "NM_ARQ": "nome_arquivo",
            "LINK_ARQ": "link_arquivo",
        }
    )
    docs["tipo_documento"] = docs["tipo_cvm"].map(_normalizar_tipo_cvm)
    docs["data_documento"] = pd.to_datetime(docs["data_documento"], errors="coerce")
    docs["data_recebimento"] = pd.to_datetime(docs["data_recebimento"], errors="coerce")
    docs = docs.dropna(subset=["cnpj_emissor", "link_arquivo", "tipo_documento"])
    return docs.drop_duplicates("link_arquivo", keep="last")


def _candidatos_cvm(row: pd.Series, docs_cvm: pd.DataFrame) -> list[tuple[str, str, float]]:
    if docs_cvm.empty or pd.isna(row.get("cnpj_emissor")):
        return []

    cnpj = str(row.get("cnpj_emissor"))
    data_oferta = pd.to_datetime(row.get("data_requerimento"), errors="coerce")
    docs = docs_cvm[docs_cvm["cnpj_emissor"].astype(str).eq(cnpj)].copy()
    if docs.empty:
        return []

    if pd.notna(data_oferta):
        inicio = data_oferta - pd.Timedelta(days=180)
        fim = data_oferta + pd.Timedelta(days=240)
        docs = docs[
            docs["data_recebimento"].between(inicio, fim)
            | docs["data_documento"].between(inicio, fim)
        ]
    if docs.empty:
        return []

    prioridade = {
        "prospecto": 1.0,
        "anuncio_inicio": 0.9,
        "aviso_mercado": 0.8,
        "relatorio_gerencial": 0.7,
    }
    docs["prioridade"] = docs["tipo_documento"].map(prioridade).fillna(0.5)
    docs = docs.sort_values(["prioridade", "data_recebimento"], ascending=[False, False])
    return [
        (row_doc["link_arquivo"], row_doc["tipo_documento"], float(row_doc["prioridade"]))
        for _, row_doc in docs.head(6).iterrows()
    ]


def _consultas_oferta(row: pd.Series) -> Iterable[str]:
    base = [
        row.get("consulta_fnet"),
        row.get("consulta_clube_fii"),
        f'{row.get("nome_emissor", "")} prospecto definitivo oferta publica FII pdf',
        f'{row.get("nome_emissor", "")} estudo de viabilidade FII pdf',
    ]
    ticker = row.get("ticker")
    if pd.notna(ticker):
        base.extend(
            [
                f"{ticker} prospecto definitivo FII pdf",
                f"{ticker} estudo de viabilidade oferta pdf",
            ]
        )
    for consulta in base:
        consulta = str(consulta or "").strip()
        if consulta:
            yield consulta

