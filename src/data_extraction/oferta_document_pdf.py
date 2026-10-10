from __future__ import annotations

import base64
import binascii
import hashlib
import json
from pathlib import Path

import requests

from data_extraction.oferta_document_common import USER_AGENT


def _extrair_pdf_bytes_de_conteudo(conteudo: bytes, content_type: str = "") -> bytes:
    prefixo = conteudo[:5]
    if prefixo == b"%PDF-":
        return conteudo

    texto = conteudo.strip().strip(b'"').strip(b"'")
    if texto[:5] == b"JVBER":
        try:
            decodificado = base64.b64decode(texto, validate=True)
        except binascii.Error:
            decodificado = base64.b64decode(texto)
        if decodificado[:5] == b"%PDF-":
            return decodificado

    if "pdf" in content_type and b"%PDF-" in conteudo[:2048]:
        return conteudo[conteudo.find(b"%PDF-") :]

    raise ValueError("Resposta nao parece ser PDF.")


def _extrair_pdf_bytes(response: requests.Response) -> bytes:
    content_type = response.headers.get("content-type", "").lower()
    return _extrair_pdf_bytes_de_conteudo(response.content, content_type)


def _arquivo_local_da_mesma_url(destino: Path, url: str) -> bool:
    metadata_path = destino.with_suffix(".json")
    if not destino.exists() or not metadata_path.exists():
        return False

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    return metadata.get("fonte_url") == url


def _baixar_pdf(url: str, destino: Path, timeout: int = 20) -> tuple[str, int]:
    if _arquivo_local_da_mesma_url(destino, url):
        try:
            conteudo_existente = _extrair_pdf_bytes_de_conteudo(destino.read_bytes())
        except ValueError:
            pass
        else:
            destino.write_bytes(conteudo_existente)
            digest = hashlib.sha256(conteudo_existente).hexdigest()
            return digest, len(conteudo_existente)

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    conteudo = _extrair_pdf_bytes(response)

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)
    digest = hashlib.sha256(conteudo).hexdigest()
    return digest, len(conteudo)


def _proximo_arquivo_documento(
    pasta_oferta: Path,
    tipo: str,
    sequencias_documento: dict[str, int],
    url: str,
) -> Path:
    while True:
        sequencias_documento[tipo] = sequencias_documento.get(tipo, 0) + 1
        arquivo = pasta_oferta / f"{tipo}_{sequencias_documento[tipo]}.pdf"
        if not arquivo.exists() or _arquivo_local_da_mesma_url(arquivo, url):
            return arquivo

