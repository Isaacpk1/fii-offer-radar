from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from data_extraction.oferta_document_manifest import (
        DOCUMENTS_DIR,
        MANIFEST_PATH,
        PROCESSED_DATA_DIR,
        gerar_manifesto_documentos_pendentes,
    )
except ModuleNotFoundError:
    from oferta_document_manifest import (
        DOCUMENTS_DIR,
        MANIFEST_PATH,
        PROCESSED_DATA_DIR,
        gerar_manifesto_documentos_pendentes,
    )


CATALOG_PATH = PROCESSED_DATA_DIR / "oferta_documentos_catalogo.csv"
CVM_DOCS_DIR = DOCUMENTS_DIR / "_cvm_eventual_cache"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
TIPOS_DOCUMENTO = {
    "estudo_viabilidade": ["estudo de viabilidade", "viabilidade"],
    "prospecto": ["prospecto definitivo", "prospecto preliminar", "prospecto"],
    "lamina": ["lamina"],
    "anuncio_inicio": ["anuncio de inicio", "inicio da oferta"],
    "material_publicitario": ["material publicitario"],
}
TERMOS_RELEVANTES = [
    "fii",
    "fundo de investimento imobiliario",
    "oferta",
    "emissao",
    *[termo for termos in TIPOS_DOCUMENTO.values() for termo in termos],
]
CVM_DOCS_URL = "https://dados.cvm.gov.br/dados/FI/DOC/EVENTUAL/DADOS/eventual_fi_{ano}.csv"
CVM_TIPOS_RELEVANTES = {
    "AID": "anuncio_inicio",
    "ANUNCIO DE INICIO": "anuncio_inicio",
    "AN??NCIO DE IN??CIO": "anuncio_inicio",
    "AVISO MERCADO": "aviso_mercado",
    "AVISO AO MERCADO": "aviso_mercado",
    "MIN PROSP DEF": "prospecto",
    "MIN PROSP PREL": "prospecto",
    "PROSPECTO DE DISTRIBUICAO": "prospecto",
    "PROSPECTO DE DISTRIBUI????O": "prospecto",
    "PROSPECTO DE FUNDOS": "prospecto",
    "RELAT GERENCIAL": "relatorio_gerencial",
    "RELATORIO GERENCIAL": "relatorio_gerencial",
    "RELAT??RIO GERENCIAL": "relatorio_gerencial",
}


@dataclass
class DocumentoBaixado:
    numero_processo: str
    cnpj_emissor: str | None
    nome_emissor: str | None
    ticker: str | None
    tipo_documento: str
    fonte_url: str
    arquivo_path: str
    hash_sha256: str
    tamanho_bytes: int
    confianca_documento: float
    status_documento: str
    baixado_em: str
    observacao: str | None = None


def _slug(texto: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", str(texto)).strip("_")
    return slug[:120] or "sem_identificador"


def _normalizar_texto(texto: str | None) -> str:
    texto = html.unescape(str(texto or "")).lower()
    texto = texto.replace("%20", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto

