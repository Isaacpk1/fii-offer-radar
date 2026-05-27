from playwright.async_api import async_playwright

from .base_scraper import BaseScraper, Noticia

URL_LISTAGEM = "https://www.infomoney.com.br/tudo-sobre/fundos-imobiliarios/"


class InfoMoneyScraper(BaseScraper):
    """Extrai noticias de FIIs do InfoMoney.

    Pagina de listagem: https://www.infomoney.com.br/tudo-sobre/fundos-imobiliarios/
    Estrutura: cards com titulo, data e link do artigo.
    """

    async def extrair_noticias(self, limite: int = 10) -> list[Noticia]:
        noticias = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(URL_LISTAGEM, wait_until="networkidle")
            await page.wait_for_selector("article, [class*='post'], [class*='card']", timeout=30_000)

            cards = await page.locator("article, [class*='post-item'], [class*='card-news']").all()

            for card in cards[:limite]:
                try:
                    titulo = await card.locator("h2, h3, [class*='title']").first.inner_text()
                    data_el = card.locator("time, [class*='date'], [class*='time']")
                    data = await data_el.first.inner_text() if await data_el.count() > 0 else ""
                    resumo_el = card.locator("p, [class*='excerpt'], [class*='summary']")
                    resumo = await resumo_el.first.inner_text() if await resumo_el.count() > 0 else ""
                    href = await card.locator("a").first.get_attribute("href")
                    url = href if href.startswith("http") else f"https://www.infomoney.com.br{href}"

                    noticias.append(Noticia(
                        titulo=titulo.strip(),
                        data=data.strip(),
                        resumo=resumo.strip(),
                        url=url,
                        fonte="InfoMoney",
                    ))
                except Exception:
                    continue

            await browser.close()

        return noticias