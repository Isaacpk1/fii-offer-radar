from playwright.async_api import async_playwright

from .base_scraper import BaseScraper, Noticia

# Valor Economico exige assinatura para conteudo completo.
# O scraper coleta titulo, data e resumo do que aparece na listagem publica.
URL_LISTAGEM = "https://valor.globo.com/financas/fundos-de-investimento/"


class ValorEconomicoScraper(BaseScraper):
    """Extrai noticias de FIIs do Valor Economico.

    Pagina de listagem: https://valor.globo.com/financas/fundos-de-investimento/
    Observacao: conteudo completo exige assinatura. O scraper coleta apenas
    titulo, data e resumo visivel na listagem publica.
    """

    async def extrair_noticias(self, limite: int = 10) -> list[Noticia]:
        noticias = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(URL_LISTAGEM, wait_until="networkidle")
            await page.wait_for_selector("[class*='feed'], [class*='list'], article", timeout=30_000)

            cards = await page.locator("article, [class*='feed-post'], [class*='list-item']").all()

            for card in cards[:limite]:
                try:
                    titulo = await card.locator("h2, h3, [class*='title']").first.inner_text()
                    data_el = card.locator("time, [class*='date']")
                    data = await data_el.first.inner_text() if await data_el.count() > 0 else ""
                    resumo_el = card.locator("p, [class*='excerpt']")
                    resumo = await resumo_el.first.inner_text() if await resumo_el.count() > 0 else ""
                    href = await card.locator("a").first.get_attribute("href")
                    url = href if href and href.startswith("http") else f"https://valor.globo.com{href}"

                    noticias.append(Noticia(
                        titulo=titulo.strip(),
                        data=data.strip(),
                        resumo=resumo.strip(),
                        url=url,
                        fonte="Valor Economico",
                    ))
                except Exception:
                    continue

            await browser.close()

        return noticias