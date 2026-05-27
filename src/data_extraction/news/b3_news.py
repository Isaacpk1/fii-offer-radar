from .base_scraper import BaseScraper, Noticia, abrir_pagina, coletar_links_noticias, fechar_pagina

URL_LISTAGEM = "https://www.b3.com.br/pt_br/noticias/"
FILTRO_FII = "FII"


class B3NewsScraper(BaseScraper):
    """Extrai noticias de FIIs do portal de noticias da B3.

    Pagina de listagem: https://www.b3.com.br/pt_br/noticias/
    Filtra apenas noticias com tag FII.
    """

    async def extrair_noticias(self, limite: int = 10) -> list[Noticia]:
        playwright, browser, page = await abrir_pagina(URL_LISTAGEM)
        try:
            return await coletar_links_noticias(
                page,
                fonte="B3",
                base_url=URL_LISTAGEM,
                limite=limite,
                url_deve_conter=["b3.com.br"],
            )
        finally:
            await fechar_pagina(playwright, browser)
