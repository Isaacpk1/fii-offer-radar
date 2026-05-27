from __future__ import annotations

import html
import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests

from data_extraction.oferta_document_common import TERMOS_RELEVANTES, TIPOS_DOCUMENTO, USER_AGENT, _normalizar_texto


def _extrair_links_busca_duckduckgo(conteudo: str) -> list[str]:
    links = []
    for match in re.finditer(r'href="([^"]+)"', conteudo):
        raw_url = html.unescape(match.group(1))
        if "uddg=" in raw_url:
            parsed = urlparse(raw_url)
            params = parse_qs(parsed.query)
            raw_url = params.get("uddg", [raw_url])[0]
        raw_url = unquote(raw_url)
        if raw_url.startswith("http") and raw_url not in links:
            links.append(raw_url)
    return links


def _extrair_links_busca_bing(conteudo: str) -> list[str]:
    links = []
    patterns = [
        r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"',
        r'<a[^>]+href="(https?://[^"]+)"',
    ]
    for pattern in patterns:
        for raw_url in re.findall(pattern, conteudo, flags=re.I):
            raw_url = html.unescape(raw_url)
            if raw_url.startswith("http") and "bing.com" not in urlparse(raw_url).netloc and raw_url not in links:
                links.append(raw_url)
    return links


def _buscar_links_bing(consulta: str, timeout: int = 30) -> list[str]:
    url = f"https://www.bing.com/search?q={quote_plus(consulta)}"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return _extrair_links_busca_bing(response.text)


def _buscar_links_duckduckgo(consulta: str, timeout: int = 30) -> list[str]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(consulta)}"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return _extrair_links_busca_duckduckgo(response.text)


def _buscar_links(consulta: str, timeout: int = 30) -> list[str]:
    links = []
    for buscador in (_buscar_links_bing, _buscar_links_duckduckgo):
        try:
            for link in buscador(consulta, timeout=timeout):
                if link not in links:
                    links.append(link)
        except requests.RequestException:
            continue
        if links:
            break
    return links


def _expandir_pdf_em_pagina(url: str, timeout: int = 30) -> list[str]:
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return []

    content_type = response.headers.get("content-type", "").lower()
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        return [url]

    base = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))
    links = []
    for match in re.finditer(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', response.text, flags=re.I):
        link = html.unescape(match.group(1))
        if link.startswith("/"):
            link = base + link
        if link.startswith("http") and link not in links:
            links.append(link)
    return links


def _classificar_documento(url: str, nome_emissor: str | None, ticker: str | None) -> tuple[str, float]:
    texto = _normalizar_texto(" ".join([url, nome_emissor or "", ticker or ""]))
    tipo = "documento_oferta"
    score = 0.0
    for tipo_doc, termos in TIPOS_DOCUMENTO.items():
        if any(_normalizar_texto(termo) in texto for termo in termos):
            tipo = tipo_doc
            score += 0.45
            break
    if "pdf" in texto:
        score += 0.2
    if ticker and _normalizar_texto(ticker) in texto:
        score += 0.15
    if nome_emissor:
        tokens_nome = [token for token in _normalizar_texto(nome_emissor).split() if len(token) >= 4]
        if tokens_nome:
            score += min(0.2, sum(token in texto for token in tokens_nome[:8]) * 0.04)
    if any(termo in texto for termo in TERMOS_RELEVANTES):
        score += 0.1
    return tipo, min(score, 1.0)

