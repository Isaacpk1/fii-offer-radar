from .base_scraper import BaseScraper, Noticia, abrir_pagina, coletar_links_noticias, fechar_pagina

URL_LISTAGEM = "https://www.infomoney.com.br/tudo-sobre/fundos-imobiliarios/"


class InfoMoneyScraper(BaseScraper):
    """Extrai noticias de FIIs do InfoMoney.

    Pagina de listagem: https://www.infomoney.com.br/tudo-sobre/fundos-imobiliarios/
    Estrutura: cards com titulo, data e link do artigo.
    """

    async def extrair_noticias(self, limite: int = 10) -> list[Noticia]:
        playwright, browser, page = await abrir_pagina(URL_LISTAGEM)
        try:
            return await coletar_links_noticias(
                page,
                fonte="InfoMoney",
                base_url=URL_LISTAGEM,
                limite=limite,
                url_deve_conter=["infomoney.com.br"],
            )
        finally:
            await fechar_pagina(playwright, browser)
