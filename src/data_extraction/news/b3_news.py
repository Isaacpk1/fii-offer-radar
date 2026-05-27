from playwright.async_api import async_playwright

from .base_scraper import BaseScraper, Noticia

URL_LISTAGEM = "https://www.b3.com.br/pt_br/noticias/"
FILTRO_FII = "FII"


class B3NewsScraper(BaseScraper):
    """Extrai noticias de FIIs do portal de noticias da B3.

    Pagina de listagem: https://www.b3.com.br/pt_br/noticias/
    Filtra apenas noticias com tag FII.
    """

    async def extrair_noticias(self, limite: int = 10) -> list[Noticia]:
        noticias = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(URL_LISTAGEM, wait_until="networkidle")
            await page.wait_for_selector("article, [class*='news'], [class*='card']", timeout=30_000)

            cards = await page.locator("article, [class*='news-item'], [class*='card']").all()

            for card in cards:
                if len(noticias) >= limite:
                    break
                try:
                    texto_card = await card.inner_text()
                    if FILTRO_FII not in texto_card.upper():
                        continue

                    titulo = await card.locator("h2, h3, [class*='title']").first.inner_text()
                    data_el = card.locator("time, [class*='date']")
                    data = await data_el.first.inner_text() if await data_el.count() > 0 else ""
                    resumo_el = card.locator("p, [class*='excerpt']")
                    resumo = await resumo_el.first.inner_text() if await resumo_el.count() > 0 else ""
                    href = await card.locator("a").first.get_attribute("href")
                    url = href if href and href.startswith("http") else f"https://www.b3.com.br{href}"

                    noticias.append(Noticia(
                        titulo=titulo.strip(),
                        data=data.strip(),
                        resumo=resumo.strip(),
                        url=url,
                        fonte="B3",
                    ))
                except Exception:
                    continue

            await browser.close()

        return noticias