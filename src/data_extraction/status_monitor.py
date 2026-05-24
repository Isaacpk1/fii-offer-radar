import json
from datetime import datetime
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_PATH = PROJECT_ROOT / "src" / "data" / "processed" / "ofertas_fiis_pronto_para_ia.csv"
STATE_PATH = PROJECT_ROOT / "src" / "data" / "processed" / "status_monitor_state.json"
ALERTS_PATH = PROJECT_ROOT / "src" / "data" / "processed" / "status_monitor_alerts.json"


def carregar_status_atual() -> dict[str, str]:
    df = pd.read_csv(PROCESSED_DATA_PATH, sep=";", encoding="utf-8")
    return dict(zip(df["Numero_Processo"].astype(str), df["Status_Requerimento"].astype(str)))


def carregar_estado_anterior() -> dict[str, str]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def salvar_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def verificar_mudancas_status() -> list[dict[str, str]]:
    """Compara o status atual do CSV processado com o snapshot anterior."""
    anterior = carregar_estado_anterior()
    atual = carregar_status_atual()
    mudancas = []

    for processo, status_atual in atual.items():
        status_anterior = anterior.get(processo)
        if status_anterior is not None and status_anterior != status_atual:
            mudancas.append(
                {
                    "Numero_Processo": processo,
                    "Status_Anterior": status_anterior,
                    "Status_Atual": status_atual,
                    "Detectado_Em": datetime.now().isoformat(timespec="seconds"),
                }
            )

    salvar_json(STATE_PATH, atual)
    salvar_json(ALERTS_PATH, mudancas)
    return mudancas


if __name__ == "__main__":
    alertas = verificar_mudancas_status()
    print(f"{len(alertas)} mudancas de status detectadas.")
