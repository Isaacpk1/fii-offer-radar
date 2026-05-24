import asyncio
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "src" / "data" / "raw"


async def extrair_ofertas_anbima(url: str, tabela_selector: str = "table") -> pd.DataFrame:
    """Extrai uma tabela publica da ANBIMA usando Playwright.

    O modulo e configuravel porque a pagina final e o seletor CSS podem mudar
    conforme a fonte de dados escolhida dentro do site da ANBIMA.
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_selector(tabela_selector, timeout=30_000)

        rows = await page.locator(f"{tabela_selector} tr").evaluate_all(
            """trs => trs.map(tr => Array.from(tr.querySelectorAll('th,td')).map(td => td.innerText.trim()))"""
        )
        await browser.close()

    if not rows:
        return pd.DataFrame()

    header = rows[0]
    data = [row for row in rows[1:] if len(row) == len(header)]
    df = pd.DataFrame(data, columns=header)

    caminho_saida = RAW_DATA_DIR / "ofertas_anbima_bruto.csv"
    df.to_csv(caminho_saida, sep=";", index=False, encoding="utf-8")
    return df


def extrair_ofertas_anbima_sync(url: str, tabela_selector: str = "table") -> pd.DataFrame:
    return asyncio.run(extrair_ofertas_anbima(url, tabela_selector))


if __name__ == "__main__":
    raise SystemExit(
        "Informe a URL da ANBIMA ou chame extrair_ofertas_anbima_sync(url, selector)."
    )
