from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
PROCESSED_DATA_DIR = SRC_DIR / "data" / "processed"
DETERMINISTIC_PATH = PROCESSED_DATA_DIR / "oferta_documentos_extracoes.csv"
LLM_EXTRACTIONS_PATH = PROCESSED_DATA_DIR / "oferta_documentos_extracoes_llm.csv"

KEYWORDS = [
    "guidance",
    "rendimento projetado",
    "rendimento alvo",
    "rendimento esperado",
    "rentabilidade alvo",
    "rentabilidade esperada",
    "rentabilidade projetada",
    "dividend yield",
    "target yield",
    "dy",
    "viabilidade",
    "distribuicao de rendimentos",
    "distribuição de rendimentos",
    "ipca +",
    "cdi +",
    "cap rate",
]


@dataclass
class DocumentoLLMExtracao:
    numero_processo: str
    cnpj_emissor: str | None
    nome_emissor: str | None
    ticker: str | None
    tipo_documento: str
    fonte_url: str
    arquivo_path: str
    texto_path: str
    preco_emissao: float | None
    rendimento_mensal_projetado_por_cota: float | None
    rendimento_anual_projetado_por_cota: float | None
    dy_projetado_oferta: float | None
    taxa_administracao: float | None
    indice_referencia: str | None
    spread_indice: float | None
    fonte_trecho: str
    confianca_extracao: float
    justificativa: str
    modelo: str
    status_extracao: str
    extraido_em: str
    observacao: str | None = None


def _normalizar_numero(valor: Any) -> float | None:
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, int | float):
        return float(valor)
    texto = str(valor).strip()
    if not texto:
        return None
    texto = re.sub(r"[^\d,.\-]", "", texto)
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _normalizar_percentual(valor: Any) -> float | None:
    numero = _normalizar_numero(valor)
    if numero is None:
        return None
    if abs(numero) > 1:
        numero = numero / 100
    if -0.5 <= numero <= 1:
        return numero
    return None


def _coletar_contexto(texto: str, limite_chars: int = 14000) -> str:
    texto_limpo = re.sub(r"\s+", " ", texto).strip()
    if len(texto_limpo) <= limite_chars:
        return texto_limpo

    partes: list[str] = []
    texto_lower = texto_limpo.lower()
    for keyword in KEYWORDS:
        inicio = 0
        while True:
            idx = texto_lower.find(keyword.lower(), inicio)
            if idx == -1:
                break
            partes.append(texto_limpo[max(0, idx - 900) : min(len(texto_limpo), idx + 1600)])
            inicio = idx + len(keyword)
            if sum(len(parte) for parte in partes) >= limite_chars:
                break
        if sum(len(parte) for parte in partes) >= limite_chars:
            break

    if not partes:
        partes = [texto_limpo[: limite_chars // 2], texto_limpo[-limite_chars // 2 :]]

    contexto = "\n\n--- TRECHO ---\n\n".join(partes)
    return contexto[:limite_chars]


def _extrair_json(texto: str) -> dict[str, Any]:
    conteudo = texto.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", conteudo, flags=re.IGNORECASE | re.DOTALL)
    if fence:
        conteudo = fence.group(1).strip()
    inicio = conteudo.find("{")
    fim = conteudo.rfind("}")
    if inicio != -1 and fim != -1 and fim > inicio:
        conteudo = conteudo[inicio : fim + 1]
    return json.loads(conteudo)


def _validar_saida(payload: dict[str, Any], preco_referencia: float | None) -> dict[str, Any]:
    preco = _normalizar_numero(payload.get("preco_emissao"))
    rendimento_mensal = _normalizar_numero(payload.get("rendimento_mensal_projetado_por_cota"))
    rendimento_anual = _normalizar_numero(payload.get("rendimento_anual_projetado_por_cota"))
    dy = _normalizar_percentual(payload.get("dy_projetado_oferta"))
    taxa_adm = _normalizar_percentual(payload.get("taxa_administracao"))
    spread = _normalizar_percentual(payload.get("spread_indice"))

    preco_base = preco_referencia or preco
    if rendimento_anual is None and rendimento_mensal is not None:
        rendimento_anual = rendimento_mensal * 12
    if dy is None and rendimento_anual is not None and preco_base and preco_base > 0:
        dy = rendimento_anual / preco_base
    if rendimento_anual is None and dy is not None and preco_base and preco_base > 0:
        rendimento_anual = dy * preco_base

    if dy is not None and not (0.01 <= dy <= 0.35):
        dy = None
    if taxa_adm is not None and not (0 <= taxa_adm <= 0.05):
        taxa_adm = None

    indice = payload.get("indice_referencia")
    indice = str(indice).upper().strip() if indice else None
    if indice not in {"IPCA", "CDI", "SELIC", "IFIX"}:
        indice = None

    confianca = _normalizar_numero(payload.get("confianca_extracao")) or 0
    confianca = max(0.0, min(float(confianca), 1.0))
    fonte_trecho = str(payload.get("fonte_trecho") or "").strip()
    justificativa = str(payload.get("justificativa") or "").strip()

    return {
        "preco_emissao": preco,
        "rendimento_mensal_projetado_por_cota": rendimento_mensal,
        "rendimento_anual_projetado_por_cota": rendimento_anual,
        "dy_projetado_oferta": dy,
        "taxa_administracao": taxa_adm,
        "indice_referencia": indice,
        "spread_indice": spread,
        "fonte_trecho": fonte_trecho[:1200],
        "confianca_extracao": confianca,
        "justificativa": justificativa[:600],
    }


def _prompt_documento(row: pd.Series, contexto: str) -> str:
    return f"""
Voce extrai campos financeiros de documentos de oferta primaria de FII.

Tarefa:
Leia os trechos do documento e retorne SOMENTE um JSON valido, sem markdown.

Campos:
- preco_emissao: preco unitario da nova emissao, em reais.
- rendimento_mensal_projetado_por_cota: rendimento/provento alvo ou projetado mensal por cota, em reais.
- rendimento_anual_projetado_por_cota: rendimento/provento alvo ou projetado anual por cota, em reais.
- dy_projetado_oferta: dividend yield/rentabilidade/rendimento alvo anual da oferta, em decimal. Ex: 11,5% = 0.115.
- taxa_administracao: taxa de administracao anual, em decimal.
- indice_referencia: IPCA, CDI, SELIC ou IFIX quando o retorno vier como indice + spread.
- spread_indice: spread anual sobre o indice, em decimal. Ex: IPCA + 7,5% = 0.075.
- fonte_trecho: copie um trecho curto do texto que prove os campos extraidos.
- confianca_extracao: numero de 0 a 1.
- justificativa: explique em uma frase curta por que interpretou assim.

Regras criticas:
1. Nao confunda taxa de administracao, taxa de distribuicao, cap rate ou taxa de performance com DY projetado.
2. Nao use rendimento historico se o texto nao indicar guidance, alvo, esperado, estimado, projetado ou estudo de viabilidade.
3. Se o documento disser que "nao ha rentabilidade alvo/esperada", deixe dy_projetado_oferta como null.
4. Se houver apenas IPCA+spread ou CDI+spread, preencha indice_referencia e spread_indice; so preencha dy_projetado_oferta se o texto tambem der um percentual total anual.
5. Se houver duvida, retorne null no campo e reduza a confianca.

Metadados:
numero_processo: {row.get("numero_processo")}
tipo_documento: {row.get("tipo_documento")}
nome_emissor: {row.get("nome_emissor")}
ticker: {row.get("ticker")}
preco_emissao_cvm: {row.get("preco_emissao_extraido")}

Trechos:
{contexto}
"""


def _linha_erro(row: pd.Series, modelo: str, status: str, observacao: str) -> DocumentoLLMExtracao:
    now = datetime.now().isoformat(timespec="seconds")
    return DocumentoLLMExtracao(
        numero_processo=str(row.get("numero_processo")),
        cnpj_emissor=row.get("cnpj_emissor"),
        nome_emissor=row.get("nome_emissor"),
        ticker=row.get("ticker"),
        tipo_documento=str(row.get("tipo_documento")),
        fonte_url=str(row.get("fonte_url") or ""),
        arquivo_path=str(row.get("arquivo_path") or ""),
        texto_path=str(row.get("texto_path") or ""),
        preco_emissao=None,
        rendimento_mensal_projetado_por_cota=None,
        rendimento_anual_projetado_por_cota=None,
        dy_projetado_oferta=None,
        taxa_administracao=None,
        indice_referencia=None,
        spread_indice=None,
        fonte_trecho="",
        confianca_extracao=0.0,
        justificativa="",
        modelo=modelo,
        status_extracao=status,
        extraido_em=now,
        observacao=observacao,
    )


def _processar_linha(row: pd.Series, llm: ChatGoogleGenerativeAI, modelo: str) -> DocumentoLLMExtracao:
    texto_path = Path(str(row.get("texto_path")))
    if not texto_path.exists():
        return _linha_erro(row, modelo, "sem_texto", f"Texto nao encontrado: {texto_path}")

    texto = texto_path.read_text(encoding="utf-8", errors="ignore")
    contexto = _coletar_contexto(texto)
    if not contexto:
        return _linha_erro(row, modelo, "sem_texto", "Texto vazio.")

    prompt = _prompt_documento(row, contexto)
    resposta = llm.invoke(prompt)
    conteudo = getattr(resposta, "content", str(resposta))
    payload = _extrair_json(conteudo)
    validado = _validar_saida(payload, _normalizar_numero(row.get("preco_emissao_extraido")))

    status = "sem_campos"
    if validado["dy_projetado_oferta"] is not None:
        status = "dy_projetado_extraido"
    elif any(
        validado[campo] is not None
        for campo in [
            "preco_emissao",
            "rendimento_mensal_projetado_por_cota",
            "rendimento_anual_projetado_por_cota",
            "taxa_administracao",
            "indice_referencia",
            "spread_indice",
        ]
    ):
        status = "parcial"

    return DocumentoLLMExtracao(
        numero_processo=str(row.get("numero_processo")),
        cnpj_emissor=row.get("cnpj_emissor"),
        nome_emissor=row.get("nome_emissor"),
        ticker=row.get("ticker"),
        tipo_documento=str(row.get("tipo_documento")),
        fonte_url=str(row.get("fonte_url") or ""),
        arquivo_path=str(row.get("arquivo_path") or ""),
        texto_path=str(texto_path),
        modelo=modelo,
        status_extracao=status,
        extraido_em=datetime.now().isoformat(timespec="seconds"),
        observacao=None,
        **validado,
    )


def extrair_documentos_com_llm(
    limite: int | None = None,
    sobrescrever: bool = False,
    modelo: str | None = None,
) -> pd.DataFrame:
    load_dotenv()
    modelo = (modelo or os.getenv("OFERTA_DOC_LLM_MODEL", "gemini-2.5-flash")).removeprefix("models/")

    if not DETERMINISTIC_PATH.exists():
        raise FileNotFoundError(f"Extracoes deterministicas nao encontradas: {DETERMINISTIC_PATH}")

    deterministicas = pd.read_csv(DETERMINISTIC_PATH, sep=";", encoding="utf-8")
    candidatos = deterministicas[
        deterministicas["status_extracao"].isin(["sem_campos", "parcial"])
        & deterministicas["texto_path"].notna()
    ].copy()
    candidatos = candidatos[candidatos["dy_projetado_oferta"].isna()]

    if not sobrescrever and LLM_EXTRACTIONS_PATH.exists():
        anteriores = pd.read_csv(LLM_EXTRACTIONS_PATH, sep=";", encoding="utf-8")
        processados = set(zip(anteriores["arquivo_path"].astype(str), anteriores["modelo"].astype(str)))
        candidatos = candidatos[
            ~candidatos.apply(lambda row: (str(row.get("arquivo_path")), modelo) in processados, axis=1)
        ]
    else:
        anteriores = pd.DataFrame()

    if limite:
        candidatos = candidatos.head(limite)

    if not os.getenv("GOOGLE_API_KEY"):
        linhas = [_linha_erro(row, modelo, "sem_api_key", "GOOGLE_API_KEY nao configurada.") for _, row in candidatos.iterrows()]
    else:
        llm = ChatGoogleGenerativeAI(model=modelo, temperature=0)
        linhas = []
        for _, row in candidatos.iterrows():
            try:
                linhas.append(_processar_linha(row, llm, modelo))
            except Exception as exc:
                linhas.append(_linha_erro(row, modelo, "erro_llm", str(exc)))

    novas = pd.DataFrame([asdict(linha) for linha in linhas])
    if not anteriores.empty and not sobrescrever:
        resultado = pd.concat([anteriores, novas], ignore_index=True)
    else:
        resultado = novas

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(LLM_EXTRACTIONS_PATH, sep=";", index=False, encoding="utf-8")
    print(f"Extracoes LLM salvas em: {LLM_EXTRACTIONS_PATH} ({len(resultado)} registros)")
    if not resultado.empty:
        print(f"DY projetado via LLM: {resultado['dy_projetado_oferta'].notna().sum()} documento(s)")
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrai campos de ofertas via LangChain/LLM.")
    parser.add_argument("--limite", type=int, default=None, help="Numero maximo de documentos nesta execucao.")
    parser.add_argument("--modelo", default=None, help="Modelo Gemini a usar. Padrao: gemini-2.5-flash.")
    parser.add_argument("--sobrescrever", action="store_true", help="Reprocessa todos os candidatos.")
    args = parser.parse_args()
    extrair_documentos_com_llm(limite=args.limite, sobrescrever=args.sobrescrever, modelo=args.modelo)


if __name__ == "__main__":
    main()
