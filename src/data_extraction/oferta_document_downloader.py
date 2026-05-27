from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_extraction.oferta_document_common import (
    CATALOG_PATH,
    DOCUMENTS_DIR,
    MANIFEST_PATH,
    PROCESSED_DATA_DIR,
    DocumentoBaixado,
    _slug,
    gerar_manifesto_documentos_pendentes,
)
from data_extraction.oferta_document_cvm import (
    _anos_para_documentos,
    _candidatos_cvm,
    _carregar_documentos_cvm,
    _consultas_oferta,
)
from data_extraction.oferta_document_pdf import _baixar_pdf, _proximo_arquivo_documento
from data_extraction.oferta_document_search import (
    _buscar_links,
    _classificar_documento,
    _expandir_pdf_em_pagina,
)


def baixar_documentos_ofertas(
    limite: int | None = None,
    max_documentos_por_oferta: int = 2,
    pausa_segundos: float = 1.0,
    confianca_minima: float = 0.45,
    ano_minimo: int | None = None,
    ordenar_por_recencia: bool = True,
) -> pd.DataFrame:
    """Busca, baixa e cataloga PDFs de ofertas pendentes a partir do manifesto."""
    if not MANIFEST_PATH.exists():
        gerar_manifesto_documentos_pendentes(limite=limite)

    manifest = pd.read_csv(MANIFEST_PATH, sep=";", encoding="utf-8")
    manifest["data_requerimento"] = pd.to_datetime(manifest["data_requerimento"], errors="coerce")
    if ano_minimo:
        manifest = manifest[manifest["data_requerimento"].dt.year >= ano_minimo]
    if ordenar_por_recencia:
        manifest = manifest.sort_values(
            ["data_requerimento", "score_priorizacao"],
            ascending=[False, False],
        )
    if limite:
        manifest = manifest.head(limite)
    docs_cvm = _carregar_documentos_cvm(_anos_para_documentos(manifest))

    catalogo: list[DocumentoBaixado] = []
    for _, row in manifest.iterrows():
        numero_processo = str(row.get("numero_processo"))
        pasta_oferta = DOCUMENTS_DIR / _slug(numero_processo)
        vistos: set[str] = set()
        sequencias_documento: dict[str, int] = {}
        baixados = 0
        consultas_com_resultado = 0

        for pdf_url, tipo, confianca in _candidatos_cvm(row, docs_cvm):
            if baixados >= max_documentos_por_oferta:
                break
            arquivo = _proximo_arquivo_documento(pasta_oferta, tipo, sequencias_documento, pdf_url)
            try:
                digest, tamanho = _baixar_pdf(pdf_url, arquivo)
            except (requests.RequestException, ValueError) as exc:
                catalogo.append(
                    DocumentoBaixado(
                        numero_processo=numero_processo,
                        cnpj_emissor=row.get("cnpj_emissor"),
                        nome_emissor=row.get("nome_emissor"),
                        ticker=row.get("ticker"),
                        tipo_documento=tipo,
                        fonte_url=pdf_url,
                        arquivo_path=str(arquivo),
                        hash_sha256="",
                        tamanho_bytes=0,
                        confianca_documento=confianca,
                        status_documento="erro_download_cvm",
                        baixado_em=datetime.now().isoformat(timespec="seconds"),
                        observacao=str(exc),
                    )
                )
                continue

            metadata = {
                "numero_processo": numero_processo,
                "cnpj_emissor": row.get("cnpj_emissor"),
                "nome_emissor": row.get("nome_emissor"),
                "ticker": row.get("ticker"),
                "tipo_documento": tipo,
                "fonte_url": pdf_url,
                "arquivo_path": str(arquivo),
                "hash_sha256": digest,
                "tamanho_bytes": tamanho,
                "confianca_documento": confianca,
                "baixado_em": datetime.now().isoformat(timespec="seconds"),
            }
            (arquivo.with_suffix(".json")).write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            catalogo.append(DocumentoBaixado(**metadata, status_documento="baixado_cvm"))
            baixados += 1

        for consulta in _consultas_oferta(row):
            if baixados >= max_documentos_por_oferta:
                break
            try:
                candidatos = _buscar_links(consulta)
            except requests.RequestException as exc:
                catalogo.append(
                    DocumentoBaixado(
                        numero_processo=numero_processo,
                        cnpj_emissor=row.get("cnpj_emissor"),
                        nome_emissor=row.get("nome_emissor"),
                        ticker=row.get("ticker"),
                        tipo_documento="busca",
                        fonte_url=consulta,
                        arquivo_path="",
                        hash_sha256="",
                        tamanho_bytes=0,
                        confianca_documento=0.0,
                        status_documento="erro_busca",
                        baixado_em=datetime.now().isoformat(timespec="seconds"),
                        observacao=str(exc),
                    )
                )
                continue
            consultas_com_resultado += int(bool(candidatos))

            pdfs: list[str] = []
            for candidato in candidatos[:8]:
                if candidato in vistos:
                    continue
                vistos.add(candidato)
                if ".pdf" in candidato.lower():
                    pdfs.append(candidato)
                else:
                    pdfs.extend(_expandir_pdf_em_pagina(candidato))

            for pdf_url in dict.fromkeys(pdfs):
                if baixados >= max_documentos_por_oferta:
                    break
                tipo, confianca = _classificar_documento(
                    pdf_url,
                    row.get("nome_emissor"),
                    row.get("ticker"),
                )
                if confianca < confianca_minima:
                    continue
                arquivo = _proximo_arquivo_documento(pasta_oferta, tipo, sequencias_documento, pdf_url)
                try:
                    digest, tamanho = _baixar_pdf(pdf_url, arquivo)
                except (requests.RequestException, ValueError) as exc:
                    catalogo.append(
                        DocumentoBaixado(
                            numero_processo=numero_processo,
                            cnpj_emissor=row.get("cnpj_emissor"),
                            nome_emissor=row.get("nome_emissor"),
                            ticker=row.get("ticker"),
                            tipo_documento=tipo,
                            fonte_url=pdf_url,
                            arquivo_path=str(arquivo),
                            hash_sha256="",
                            tamanho_bytes=0,
                            confianca_documento=confianca,
                            status_documento="erro_download",
                            baixado_em=datetime.now().isoformat(timespec="seconds"),
                            observacao=str(exc),
                        )
                    )
                    continue

                metadata = {
                    "numero_processo": numero_processo,
                    "cnpj_emissor": row.get("cnpj_emissor"),
                    "nome_emissor": row.get("nome_emissor"),
                    "ticker": row.get("ticker"),
                    "tipo_documento": tipo,
                    "fonte_url": pdf_url,
                    "arquivo_path": str(arquivo),
                    "hash_sha256": digest,
                    "tamanho_bytes": tamanho,
                    "confianca_documento": confianca,
                    "baixado_em": datetime.now().isoformat(timespec="seconds"),
                }
                (arquivo.with_suffix(".json")).write_text(
                    json.dumps(metadata, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                catalogo.append(
                    DocumentoBaixado(
                        **metadata,
                        status_documento="baixado",
                    )
                )
                baixados += 1

            time.sleep(pausa_segundos)

        if baixados == 0 and consultas_com_resultado == 0:
            catalogo.append(
                DocumentoBaixado(
                    numero_processo=numero_processo,
                    cnpj_emissor=row.get("cnpj_emissor"),
                    nome_emissor=row.get("nome_emissor"),
                    ticker=row.get("ticker"),
                    tipo_documento="busca",
                    fonte_url="",
                    arquivo_path="",
                    hash_sha256="",
                    tamanho_bytes=0,
                    confianca_documento=0.0,
                    status_documento="sem_resultado_busca",
                    baixado_em=datetime.now().isoformat(timespec="seconds"),
                    observacao="Nenhum link candidato encontrado nas consultas geradas.",
                )
            )
        elif baixados == 0:
            catalogo.append(
                DocumentoBaixado(
                    numero_processo=numero_processo,
                    cnpj_emissor=row.get("cnpj_emissor"),
                    nome_emissor=row.get("nome_emissor"),
                    ticker=row.get("ticker"),
                    tipo_documento="busca",
                    fonte_url="",
                    arquivo_path="",
                    hash_sha256="",
                    tamanho_bytes=0,
                    confianca_documento=0.0,
                    status_documento="sem_pdf_confiavel",
                    baixado_em=datetime.now().isoformat(timespec="seconds"),
                    observacao="Busca retornou links, mas nenhum PDF passou no filtro de confianca.",
                )
            )

    df_catalogo = pd.DataFrame([item.__dict__ for item in catalogo])
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not df_catalogo.empty:
        df_catalogo.to_csv(CATALOG_PATH, sep=";", index=False, encoding="utf-8")
    else:
        df_catalogo = pd.DataFrame(
            columns=[
                "numero_processo",
                "cnpj_emissor",
                "nome_emissor",
                "ticker",
                "tipo_documento",
                "fonte_url",
                "arquivo_path",
                "hash_sha256",
                "tamanho_bytes",
                "confianca_documento",
                "status_documento",
                "baixado_em",
                "observacao",
            ]
        )
        df_catalogo.to_csv(CATALOG_PATH, sep=";", index=False, encoding="utf-8")

    print(f"Catalogo de documentos salvo em: {CATALOG_PATH} ({len(df_catalogo)} registros)")
    baixados = (
        df_catalogo["status_documento"].isin(["baixado", "baixado_cvm"]).sum()
        if not df_catalogo.empty
        else 0
    )
    print(f"PDFs baixados: {baixados}")
    return df_catalogo


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa e cataloga PDFs de ofertas de FIIs.")
    parser.add_argument("--limite", type=int, default=10, help="Numero maximo de ofertas a processar.")
    parser.add_argument("--max-docs", type=int, default=2, help="Numero maximo de PDFs por oferta.")
    parser.add_argument("--pausa", type=float, default=1.0, help="Pausa entre buscas, em segundos.")
    parser.add_argument("--confianca", type=float, default=0.45, help="Confianca minima para baixar um PDF.")
    parser.add_argument("--ano-minimo", type=int, default=2026, help="Ano minimo da data de requerimento.")
    parser.add_argument(
        "--por-score",
        action="store_true",
        help="Mantem a ordem do manifesto em vez de priorizar ofertas mais recentes.",
    )
    args = parser.parse_args()
    baixar_documentos_ofertas(
        limite=args.limite,
        max_documentos_por_oferta=args.max_docs,
        pausa_segundos=args.pausa,
        confianca_minima=args.confianca,
        ano_minimo=args.ano_minimo,
        ordenar_por_recencia=not args.por_score,
    )


if __name__ == "__main__":
    main()
