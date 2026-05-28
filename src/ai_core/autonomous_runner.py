"""
Runner autonomo do agente de FIIs.

Execute:
    python src/ai_core/autonomous_runner.py

Opcoes:
    python src/ai_core/autonomous_runner.py --send-email
    python src/ai_core/autonomous_runner.py --loop --interval-minutes 1440
"""

from __future__ import annotations

import argparse
import json
import os
import smtplib
import sys
import time
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_core.agent import inicializar_agente_analista


load_dotenv()

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


def _resposta_para_texto(resposta: Any) -> str:
    if isinstance(resposta, dict):
        output = resposta.get("output", resposta)
    else:
        output = resposta
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        partes = []
        for item in output:
            if isinstance(item, dict):
                partes.append(str(item.get("text") or item.get("content") or item))
            else:
                partes.append(str(item))
        return "\n".join(partes)
    return str(output)


def executar_tarefa(agente, tarefa: dict[str, str]) -> dict[str, Any]:
    print(f"[{datetime.now():%H:%M}] Executando: {tarefa['nome']}")
    resposta = agente.invoke({"input": tarefa["prompt"]})
    texto = _resposta_para_texto(resposta)

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


def _carregar_smtp_config() -> dict[str, Any] | None:
    host = os.getenv("SMTP_HOST", "").strip()
    port = os.getenv("SMTP_PORT", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip()
    to = os.getenv("ALERT_EMAIL_TO", "").strip()
    if not all([host, port, sender, to]):
        return None

    return {
        "host": host,
        "port": int(port),
        "from": sender,
        "to": to,
        "username": os.getenv("SMTP_USERNAME", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "use_tls": os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "sim"},
    }


def enviar_email_alerta(resultado: dict[str, Any], smtp_config: dict[str, Any]) -> bool:
    alertas = resultado.get("resultado", {}).get("alertas_urgentes", [])
    if not alertas:
        return False

    corpo = f"Alertas automaticos FII - {datetime.now():%d/%m/%Y}\n\n"
    for alerta in alertas:
        corpo += f"- {alerta}\n"

    msg = MIMEText(corpo)
    msg["Subject"] = f"[FII-Agent] {len(alertas)} alerta(s) urgente(s)"
    msg["From"] = smtp_config["from"]
    msg["To"] = smtp_config["to"]

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as smtp:
        if smtp_config.get("use_tls"):
            smtp.starttls()
        if smtp_config.get("username") and smtp_config.get("password"):
            smtp.login(smtp_config["username"], smtp_config["password"])
        smtp.sendmail(smtp_config["from"], smtp_config["to"], msg.as_string())
    return True


def run_once(send_email: bool = False) -> list[Path]:
    print(f"=== Runner autonomo iniciado: {datetime.now():%Y-%m-%d %H:%M} ===")
    agente = inicializar_agente_analista()
    smtp_config = _carregar_smtp_config() if send_email else None
    arquivos = []

    for tarefa in TAREFAS_DIARIAS:
        resultado = executar_tarefa(agente, tarefa)
        caminho = salvar_alerta(resultado)
        arquivos.append(caminho)
        print(f"  Salvo: {caminho}")
        if smtp_config and enviar_email_alerta(resultado, smtp_config):
            print(f"  E-mail enviado para {smtp_config['to']}")
        elif send_email and tarefa["nome"] == "triagem_diaria" and smtp_config is None:
            print("  E-mail nao enviado: configure SMTP_HOST, SMTP_PORT, SMTP_FROM e ALERT_EMAIL_TO.")

    print("=== Runner concluido ===")
    return arquivos


def run(loop: bool = False, interval_minutes: int = 1440, send_email: bool = False) -> None:
    if not loop:
        run_once(send_email=send_email)
        return

    while True:
        run_once(send_email=send_email)
        print(f"Proxima execucao em {interval_minutes} minuto(s).")
        time.sleep(max(1, interval_minutes) * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runner autonomo/agendavel do agente de FIIs.")
    parser.add_argument("--loop", action="store_true", help="Mantem o runner em execucao continua.")
    parser.add_argument("--interval-minutes", type=int, default=1440, help="Intervalo do loop em minutos.")
    parser.add_argument("--send-email", action="store_true", help="Envia e-mail quando houver alertas urgentes.")
    args = parser.parse_args()
    run(loop=args.loop, interval_minutes=args.interval_minutes, send_email=args.send_email)
