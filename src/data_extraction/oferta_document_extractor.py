from __future__ import annotations

import argparse
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
PROCESSED_DATA_DIR = SRC_DIR / "data" / "processed"
TEXT_DIR = PROCESSED_DATA_DIR / "oferta_documentos_texto"
CATALOG_PATH = PROCESSED_DATA_DIR / "oferta_documentos_catalogo.csv"
EXTRACTIONS_PATH = PROCESSED_DATA_DIR / "oferta_documentos_extracoes.csv"

STATUS_BAIXADO = {"baixado", "baixado_cvm"}
TIPO_PRIORIDADE = {
    "prospecto": 4,
    "estudo_viabilidade": 4,
    "anuncio_inicio": 3,
    "aviso_mercado": 2,
}


@dataclass
class DocumentoExtracao:
    numero_processo: str
    cnpj_emissor: str | None
    nome_emissor: str | None
    ticker: str | None
    tipo_documento: str
    fonte_url: str
    arquivo_path: str
    texto_path: str
    paginas_lidas: int
    caracteres_extraidos: int
    preco_emissao_extraido: float | None
    rendimento_mensal_projetado_por_cota: float | None
    rendimento_anual_projetado_por_cota: float | None
    dy_projetado_oferta: float | None
    taxa_administracao: float | None
    fonte_trecho: str
    confianca_extracao: float
    metodo: str
    status_extracao: str
    extraido_em: str
    observacao: str | None = None


def _normalizar_numero(valor: str | None) -> float | None:
    if not valor:
        return None
    texto = valor.strip()
    texto = re.sub(r"[^\d,.\-]", "", texto)
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _normalizar_percentual(valor: str | None) -> float | None:
    numero = _normalizar_numero(valor)
    if numero is None:
        return None
    if abs(numero) > 1:
        numero = numero / 100
    if -0.5 <= numero <= 1.0:
        return numero
    return None


def _ler_pdf(path: Path, max_paginas: int | None = None) -> tuple[str, int]:
    reader = PdfReader(str(path))
    paginas = reader.pages[:max_paginas] if max_paginas else reader.pages
    textos = []
    for page in paginas:
        textos.append(page.extract_text() or "")
    return "\n".join(textos), len(paginas)


def _janela(texto: str, inicio: int, fim: int, raio: int = 360) -> str:
    return re.sub(r"\s+", " ", texto[max(0, inicio - raio) : min(len(texto), fim + raio)]).strip()


def _extrair_preco_emissao(texto: str) -> tuple[float | None, str, float]:
    padroes = [
        r"pre[cç]o\s+(?:unit[aá]rio\s+de\s+)?emiss[aã]o.{0,140}?R\$\s*([\d.]+,\d{2})",
        r"R\$\s*([\d.]+,\d{2}).{0,80}?pre[cç]o\s+(?:unit[aá]rio\s+de\s+)?emiss[aã]o",
        r"valor\s+nominal\s+unit[aá]rio.{0,140}?R\$\s*([\d.]+,\d{2})",
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, flags=re.IGNORECASE | re.DOTALL)
        if match:
            valor = _normalizar_numero(match.group(1))
            if valor and 0 < valor < 100000:
                return valor, _janela(texto, match.start(), match.end()), 0.85
    return None, "", 0.0


def _extrair_rendimento_por_cota(texto: str) -> tuple[float | None, float | None, str, float]:
    padroes = [
        (
            "mensal",
            r"(?:rendimento|distribui[cç][aã]o).{0,90}?(?:mensal|m[eê]s|a\.m\.).{0,90}?R\$\s*([\d.]+,\d{2})",
            0.65,
        ),
        (
            "mensal",
            r"R\$\s*([\d.]+,\d{2}).{0,90}?(?:por\s+cota).{0,90}?(?:mensal|m[eê]s|a\.m\.)",
            0.6,
        ),
        (
            "anual",
            r"(?:rendimento|distribui[cç][aã]o).{0,90}?(?:anual|ano|a\.a\.).{0,90}?R\$\s*([\d.]+,\d{2})",
            0.65,
        ),
    ]
    for periodicidade, padrao, confianca in padroes:
        for match in re.finditer(padrao, texto, flags=re.IGNORECASE | re.DOTALL):
            trecho = _janela(texto, match.start(), match.end())
            if re.search(r"n[aã]o\s+(?:representa|deve)|garantia|promessa", trecho, flags=re.IGNORECASE):
                continue
            if not re.search(
                r"projetad[ao]|guidance|estimad[ao]|esperad[ao]|alvo|viabilidade",
                trecho,
                flags=re.IGNORECASE,
            ):
                continue
            valor = _normalizar_numero(match.group(1))
            if valor and 0 < valor < 1000:
                if periodicidade == "mensal":
                    return valor, valor * 12, trecho, confianca
                return None, valor, trecho, confianca
    return None, None, "", 0.0


def _extrair_dy_projetado(texto: str) -> tuple[float | None, str, float]:
    padroes = [
        r"(?:dividend\s*yield|dy|rentabilidade|rendimento).{0,120}?(?:projetad[ao]|esperad[ao]|estimad[ao]|alvo).{0,120}?([\d]+(?:[.,]\d+)?)\s*%\s*(?:a\.a\.|ao\s+ano|anual)?",
        r"([\d]+(?:[.,]\d+)?)\s*%\s*(?:a\.a\.|ao\s+ano|anual).{0,120}?(?:dividend\s*yield|dy|rentabilidade|rendimento).{0,120}?(?:projetad[ao]|esperad[ao]|estimad[ao]|alvo)",
    ]
    for padrao in padroes:
        for match in re.finditer(padrao, texto, flags=re.IGNORECASE | re.DOTALL):
            trecho = _janela(texto, match.start(), match.end())
            if re.search(r"n[aã]o\s+(?:representa|deve)|garantia|promessa", trecho, flags=re.IGNORECASE):
                continue
            valor = _normalizar_percentual(match.group(1))
            if valor and 0 < valor < 0.5:
                return valor, trecho, 0.7
    return None, "", 0.0


def _extrair_taxa_administracao(texto: str) -> tuple[float | None, str, float]:
    padrao = r"taxa\s+de\s+administra[cç][aã]o.{0,160}?([\d]+(?:[.,]\d+)?)\s*%\s*(?:a\.a\.|ao\s+ano|anual)?"
    match = re.search(padrao, texto, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None, "", 0.0
    valor = _normalizar_percentual(match.group(1))
    if valor is None:
        return None, "", 0.0
    if not 0 <= valor <= 0.05:
        return None, "", 0.0
    return valor, _janela(texto, match.start(), match.end()), 0.45


def _extrair_documento(row: pd.Series, max_paginas: int | None = None) -> DocumentoExtracao:
    arquivo = Path(str(row.get("arquivo_path")))
    now = datetime.now().isoformat(timespec="seconds")
    base = {
        "numero_processo": str(row.get("numero_processo")),
        "cnpj_emissor": row.get("cnpj_emissor"),
        "nome_emissor": row.get("nome_emissor"),
        "ticker": row.get("ticker"),
        "tipo_documento": str(row.get("tipo_documento")),
        "fonte_url": str(row.get("fonte_url") or ""),
        "arquivo_path": str(arquivo),
        "texto_path": "",
        "paginas_lidas": 0,
        "caracteres_extraidos": 0,
        "preco_emissao_extraido": None,
        "rendimento_mensal_projetado_por_cota": None,
        "rendimento_anual_projetado_por_cota": None,
        "dy_projetado_oferta": None,
        "taxa_administracao": None,
        "fonte_trecho": "",
        "confianca_extracao": 0.0,
        "metodo": "regex_pdf_texto_pypdf",
        "status_extracao": "erro",
        "extraido_em": now,
        "observacao": None,
    }

    try:
        texto, paginas = _ler_pdf(arquivo, max_paginas=max_paginas)
    except Exception as exc:
        base["observacao"] = str(exc)
        return DocumentoExtracao(**base)

    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", base["numero_processo"])
    texto_path = TEXT_DIR / slug / f"{arquivo.stem}.txt"
    texto_path.parent.mkdir(parents=True, exist_ok=True)
    texto_path.write_text(texto, encoding="utf-8")

    preco, trecho_preco, confianca_preco = _extrair_preco_emissao(texto)
    rendimento_mensal, rendimento_anual, trecho_rendimento, confianca_rendimento = _extrair_rendimento_por_cota(texto)
    dy, trecho_dy, confianca_dy = _extrair_dy_projetado(texto)
    taxa_adm, trecho_taxa, confianca_taxa = _extrair_taxa_administracao(texto)

    if dy is None and rendimento_anual is not None and preco:
        dy = rendimento_anual / preco
        confianca_dy = min(0.8, confianca_rendimento + confianca_preco / 4)

    trechos = [trecho for trecho in [trecho_dy, trecho_rendimento, trecho_preco, trecho_taxa] if trecho]
    confianca = max(confianca_dy, confianca_rendimento, confianca_preco * 0.35, confianca_taxa)
    if dy is not None:
        status = "dy_projetado_extraido"
    elif any(value is not None for value in [preco, rendimento_anual, taxa_adm]):
        status = "parcial"
    else:
        status = "sem_campos"

    base.update(
        {
            "texto_path": str(texto_path),
            "paginas_lidas": paginas,
            "caracteres_extraidos": len(texto),
            "preco_emissao_extraido": preco,
            "rendimento_mensal_projetado_por_cota": rendimento_mensal,
            "rendimento_anual_projetado_por_cota": rendimento_anual,
            "dy_projetado_oferta": dy,
            "taxa_administracao": taxa_adm,
            "fonte_trecho": " | ".join(trechos)[:1200],
            "confianca_extracao": round(float(confianca), 4),
            "status_extracao": status,
        }
    )
    return DocumentoExtracao(**base)


def extrair_documentos_ofertas(max_paginas: int | None = None) -> pd.DataFrame:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Catalogo nao encontrado: {CATALOG_PATH}")

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    catalogo = pd.read_csv(CATALOG_PATH, sep=";", encoding="utf-8")
    if catalogo.empty:
        extracoes = pd.DataFrame()
        extracoes.to_csv(EXTRACTIONS_PATH, sep=";", index=False, encoding="utf-8")
        return extracoes

    catalogo = catalogo[catalogo["status_documento"].isin(STATUS_BAIXADO)].copy()
    catalogo["prioridade_tipo"] = catalogo["tipo_documento"].map(TIPO_PRIORIDADE).fillna(1)
    catalogo = catalogo.sort_values(
        ["numero_processo", "prioridade_tipo", "confianca_documento", "tamanho_bytes"],
        ascending=[True, False, False, False],
    )

    extracoes = pd.DataFrame([asdict(_extrair_documento(row, max_paginas=max_paginas)) for _, row in catalogo.iterrows()])
    extracoes.to_csv(EXTRACTIONS_PATH, sep=";", index=False, encoding="utf-8")
    print(f"Extracoes de documentos salvas em: {EXTRACTIONS_PATH} ({len(extracoes)} registros)")
    if not extracoes.empty:
        print(f"DY projetado extraido: {extracoes['dy_projetado_oferta'].notna().sum()} documento(s)")
        print(f"Campos parciais extraidos: {(extracoes['status_extracao'] == 'parcial').sum()} documento(s)")
    return extracoes


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrai campos estruturados de PDFs de ofertas.")
    parser.add_argument("--max-paginas", type=int, default=None, help="Limita paginas lidas por PDF.")
    args = parser.parse_args()
    extrair_documentos_ofertas(max_paginas=args.max_paginas)


if __name__ == "__main__":
    main()
