from .base_scraper import BaseScraper, Noticia, abrir_pagina, coletar_links_noticias, fechar_pagina

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
        playwright, browser, page = await abrir_pagina(URL_LISTAGEM)
        try:
            return await coletar_links_noticias(
                page,
                fonte="Valor Economico",
                base_url=URL_LISTAGEM,
                limite=limite,
                url_deve_conter=["valor.globo.com"],
            )
        finally:
            await fechar_pagina(playwright, browser)
