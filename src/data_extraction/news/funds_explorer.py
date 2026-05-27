from .base_scraper import BaseScraper, Noticia, abrir_pagina, coletar_links_noticias, fechar_pagina

URL_LISTAGEM = "https://www.fundsexplorer.com.br/c/fiis"


class FundsExplorerScraper(BaseScraper):
    """Extrai noticias de FIIs do Funds Explorer.

    Pagina de listagem: https://www.fundsexplorer.com.br/c/fiis
    Estrutura: cards com titulo, data (DD.MM.YYYY), categoria e link do artigo.
    """

    async def extrair_noticias(self, limite: int = 10) -> list[Noticia]:
        playwright, browser, page = await abrir_pagina(URL_LISTAGEM)
        try:
            return await coletar_links_noticias(
                page,
                fonte="Funds Explorer",
                base_url=URL_LISTAGEM,
                limite=limite,
                url_deve_conter=["fundsexplorer.com.br"],
            )
        finally:
            await fechar_pagina(playwright, browser)
