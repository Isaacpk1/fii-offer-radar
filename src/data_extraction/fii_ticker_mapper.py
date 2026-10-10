from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "src" / "data" / "raw"
CACHE_PATH = RAW_DATA_DIR / "fii_cnpj_ticker_map.csv"
CACHE_TTL = timedelta(days=30)

FUNDAMENTUS_BASE_URL = "https://www.fundamentus.com.br"
FII_LIST_URL = f"{FUNDAMENTUS_BASE_URL}/fii_resultado.php"
DETAIL_URL = f"{FUNDAMENTUS_BASE_URL}/detalhes.php"
REQUEST_TIMEOUT = 30
MAX_WORKERS = 8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}

LOGGER = logging.getLogger(__name__)


def _normalizar_cnpj(cnpj: str | None) -> str | None:
    if not isinstance(cnpj, str):
        return None

    digitos = re.sub(r"\D", "", cnpj)
    if len(digitos) != 14:
        return None
    return digitos


def _formatar_cnpj(cnpj_normalizado: str) -> str:
    return (
        f"{cnpj_normalizado[:2]}.{cnpj_normalizado[2:5]}."
        f"{cnpj_normalizado[5:8]}/{cnpj_normalizado[8:12]}-"
        f"{cnpj_normalizado[12:]}"
    )


def _sessao_http() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def _buscar_html(session: requests.Session, url: str, params: dict[str, str] | None = None) -> str:
    response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "ISO-8859-1"
    return response.text


def _extrair_tickers_listagem(html: str) -> list[str]:
    tickers = {
        match.group(1).upper()
        for match in re.finditer(r"detalhes\.php\?papel=([A-Z0-9]{5,8})", html, flags=re.IGNORECASE)
    }
    return sorted(ticker for ticker in tickers if re.fullmatch(r"[A-Z]{4}\d{2}", ticker))


def _extrair_cnpj_detalhe(html: str) -> str | None:
    match = re.search(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b", html)
    return _normalizar_cnpj(match.group(1)) if match else None


def _buscar_tickers_fii(session: requests.Session) -> list[str]:
    html = _buscar_html(session, FII_LIST_URL)
    return _extrair_tickers_listagem(html)


def _buscar_cnpj_por_ticker(ticker: str) -> tuple[str, str] | None:
    try:
        session = _sessao_http()
        html = _buscar_html(session, DETAIL_URL, {"papel": ticker})
        cnpj = _extrair_cnpj_detalhe(html)
        if cnpj:
            return cnpj, ticker
    except Exception as exc:
        LOGGER.debug("Falha ao buscar CNPJ do ticker %s: %s", ticker, exc)
    return None


def _carregar_cache(permitir_stale: bool = False) -> dict[str, str] | None:
    if not CACHE_PATH.exists():
        return None

    if not permitir_stale:
        atualizado_em = datetime.fromtimestamp(CACHE_PATH.stat().st_mtime)
        if datetime.now() - atualizado_em > CACHE_TTL:
            return None

    try:
        df = pd.read_csv(CACHE_PATH, sep=";", dtype=str)
    except Exception as exc:
        LOGGER.warning("Falha ao ler cache CNPJ->Ticker em %s: %s", CACHE_PATH, exc)
        return None

    colunas_necessarias = {"cnpj", "ticker"}
    if df.empty or not colunas_necessarias.issubset(df.columns):
        return None

    df["cnpj_normalizado"] = df["cnpj"].map(_normalizar_cnpj)
    df["ticker"] = df["ticker"].astype(str).str.upper().str.replace(".SA", "", regex=False)
    df = df.dropna(subset=["cnpj_normalizado", "ticker"]).drop_duplicates("cnpj_normalizado", keep="last")
    return dict(zip(df["cnpj_normalizado"], df["ticker"])) or None


def _salvar_cache(mapeamento: dict[str, str]) -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {"cnpj": _formatar_cnpj(cnpj), "ticker": ticker}
            for cnpj, ticker in sorted(mapeamento.items(), key=lambda item: item[1])
        ]
    )
    df.to_csv(CACHE_PATH, sep=";", index=False, encoding="utf-8")


def _construir_mapeamento_fundamentus() -> dict[str, str]:
    session = _sessao_http()
    tickers = _buscar_tickers_fii(session)
    if not tickers:
        return {}

    mapeamento: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_buscar_cnpj_por_ticker, ticker): ticker for ticker in tickers}
        for future in as_completed(futures):
            resultado = future.result()
            if resultado is None:
                continue
            cnpj, ticker = resultado
            ticker_atual = mapeamento.get(cnpj)
            if ticker_atual is None or (ticker.endswith("11") and not ticker_atual.endswith("11")):
                mapeamento[cnpj] = ticker

    return mapeamento


@lru_cache(maxsize=1)
def get_cnpj_ticker_map() -> dict[str, str]:
    """Retorna o mapa CNPJ normalizado -> ticker, carregado uma unica vez por processo."""
    cache = _carregar_cache()
    if cache:
        return cache

    try:
        mapeamento = _construir_mapeamento_fundamentus()
        if mapeamento:
            _salvar_cache(mapeamento)
            return mapeamento
    except Exception as exc:
        LOGGER.warning("Falha ao construir mapa dinamico CNPJ->Ticker: %s", exc)

    cache_stale = _carregar_cache(permitir_stale=True)
    return cache_stale or {}


def get_ticker_by_cnpj(cnpj: str) -> str | None:
    """Busca o ticker B3 de um FII pelo CNPJ, sem inferencia por nome."""
    cnpj_normalizado = _normalizar_cnpj(cnpj)
    if not cnpj_normalizado:
        return None
    return get_cnpj_ticker_map().get(cnpj_normalizado)
