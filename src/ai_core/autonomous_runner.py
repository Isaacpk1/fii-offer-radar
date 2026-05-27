"""
Runner autonomo do agente de FIIs.

Execute:
    python src/ai_core/autonomous_runner.py

Agendamento exemplo:
    0 7 * * 1-5 python /path/src/ai_core/autonomous_runner.py
"""

from __future__ import annotations

import json
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any


SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_core.agent import inicializar_agente_analista


ALERTAS_DIR = Path(__file__).resolve().parents[1] / "data" / "alertas_autonomos"
ALERTAS_DIR.mkdir(parents=True, exist_ok=True)

TAREFAS_DIARIAS = [
    {
        "nome": "triagem_diaria",
        "prompt": """
Execute a triagem diaria completa:
1. Use rankear_com_diagnostico(10) para listar as top 10 ofertas.
2. Use buscar_macro_atual('selic') e buscar_macro_atual('cdi').
3. Identifique ofertas com score_priorizacao > 70 e confianca_total < 55 como gap de dados urgente.
4. Retorne APENAS JSON valido com:
{
  "alertas_urgentes": [],
  "resumo_mercado": "str",
  "acao_recomendada": "str"
}
""",
    },
    {
        "nome": "qualidade_dados",
        "prompt": """
Use resumir_qualidade_base('oferta_inteligencia').
Identifique as 3 colunas com menor cobertura.
Retorne APENAS JSON valido com:
{
  "colunas_criticas": [],
  "impacto": "str",
  "recomendacao_tecnica": "str"
}
""",
    },
]


def _extrair_json(texto: str) -> dict[str, Any]:
    cleaned = texto.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()

    inicio = cleaned.find("{")
    fim = cleaned.rfind("}")
    if inicio != -1 and fim != -1 and fim > inicio:
        cleaned = cleaned[inicio : fim + 1]
    return json.loads(cleaned)


def executar_tarefa(agente, tarefa: dict[str, str]) -> dict[str, Any]:
    print(f"[{datetime.now():%H:%M}] Executando: {tarefa['nome']}")
    resposta = agente.invoke({"input": tarefa["prompt"]})
    texto = resposta.get("output", "")

    try:
        resultado = _extrair_json(texto)
    except json.JSONDecodeError:
        resultado = {"raw": texto}

    return {
        "tarefa": tarefa["nome"],
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "resultado": resultado,
    }


def salvar_alerta(resultado: dict[str, Any]) -> Path:
    nome = f"{resultado['tarefa']}_{datetime.now():%Y%m%d_%H%M}.json"
    caminho = ALERTAS_DIR / nome
    caminho.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho


def enviar_email_alerta(resultado: dict[str, Any], destinatario: str, smtp_config: dict[str, Any]) -> None:
    alertas = resultado.get("resultado", {}).get("alertas_urgentes", [])
    if not alertas:
        return

    corpo = f"Alertas automaticos FII - {datetime.now():%d/%m/%Y}\n\n"
    for alerta in alertas:
        corpo += f"- {alerta}\n"

    msg = MIMEText(corpo)
    msg["Subject"] = f"[FII-Agent] {len(alertas)} alerta(s) urgente(s)"
    msg["From"] = smtp_config["from"]
    msg["To"] = destinatario

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as smtp:
        smtp.sendmail(smtp_config["from"], destinatario, msg.as_string())


def run() -> None:
    print(f"=== Runner autonomo iniciado: {datetime.now():%Y-%m-%d %H:%M} ===")
    agente = inicializar_agente_analista()

    for tarefa in TAREFAS_DIARIAS:
        resultado = executar_tarefa(agente, tarefa)
        caminho = salvar_alerta(resultado)
        print(f"  Salvo: {caminho}")

    print("=== Runner concluido ===")


if __name__ == "__main__":
    run()
