from playwright.async_api import async_playwright

from .base_scraper import BaseScraper, Noticia

URL_LISTAGEM = "https://www.fundsexplorer.com.br/c/fiis"


class FundsExplorerScraper(BaseScraper):
    """Extrai noticias de FIIs do Funds Explorer.

    Pagina de listagem: https://www.fundsexplorer.com.br/c/fiis
    Estrutura: cards com titulo, data (DD.MM.YYYY), categoria e link do artigo.
    """

    async def extrair_noticias(self, limite: int = 10) -> list[Noticia]:
        noticias = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(URL_LISTAGEM, wait_until="networkidle")
            await page.wait_for_selector("article", timeout=30_000)

            cards = await page.locator("article").all()

            for card in cards[:limite]:
                try:
                    titulo = await card.locator("h2, h3").first.inner_text()
                    data = await card.locator("time, [class*='date']").first.inner_text()
                    resumo_el = card.locator("p")
                    resumo = await resumo_el.first.inner_text() if await resumo_el.count() > 0 else ""
                    href = await card.locator("a").first.get_attribute("href")
                    url = href if href.startswith("http") else f"https://www.fundsexplorer.com.br{href}"

                    noticias.append(Noticia(
                        titulo=titulo.strip(),
                        data=data.strip(),
                        resumo=resumo.strip(),
                        url=url,
                        fonte="Funds Explorer",
                    ))
                except Exception:
                    continue

            await browser.close()

        return noticias