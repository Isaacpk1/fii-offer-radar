import asyncio
import json
from datetime import datetime
from pathlib import Path

from .b3_news import B3NewsScraper
from .funds_explorer import FundsExplorerScraper
from .infomoney import InfoMoneyScraper
from .valor_economico import ValorEconomicoScraper


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = PROJECT_ROOT / "src" / "data" / "processed" / "noticias_fiis.json"

SCRAPERS = [
    FundsExplorerScraper(),
    InfoMoneyScraper(),
    ValorEconomicoScraper(),
    B3NewsScraper(),
]


async def agregar_noticias(limite_por_fonte: int = 10) -> list[dict]:
    """Roda todos os scrapers em paralelo e consolida as noticias."""
    tarefas = [scraper.extrair_noticias(limite_por_fonte) for scraper in SCRAPERS]
    resultados = await asyncio.gather(*tarefas, return_exceptions=True)

    noticias = []
    for resultado in resultados:
        if isinstance(resultado, Exception):
            print(f"Aviso: um scraper falhou — {resultado}")
            continue
        noticias.extend([vars(n) for n in resultado])

    noticias.sort(key=lambda n: n.get("data", ""), reverse=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps({"atualizado_em": datetime.now().isoformat(), "noticias": noticias},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"{len(noticias)} noticias salvas em: {OUTPUT_PATH}")
    return noticias


def agregar_noticias_sync(limite_por_fonte: int = 10) -> list[dict]:
    return asyncio.run(agregar_noticias(limite_por_fonte))


if __name__ == "__main__":
    agregar_noticias_sync()