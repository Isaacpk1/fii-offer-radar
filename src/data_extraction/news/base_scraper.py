from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urljoin

from playwright.async_api import Browser, Page, Playwright, async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
NEWS_KEYWORDS = [
    "fii",
    "fiis",
    "fundo imobiliario",
    "fundos imobiliarios",
    "imobiliario",
    "imobiliarios",
    "cvm",
    "oferta",
    "emissao",
    "dividend",
    "rendimento",
]
BLOCKED_TITLE_TERMS = [
    "comparador",
    "planilha",
    "snapshot",
    "newsletter",
    "calculadora",
    "simulador",
]
BLOCKED_URL_TERMS = [
    "/ferramentas/",
    "/cl/",
    "utm_campaign",
    "lp.",
]


@dataclass
class Noticia:
    titulo: str
    data: str
    resumo: str
    url: str
    fonte: str


class BaseScraper(ABC):
    """Contrato que todo scraper de noticias deve implementar."""

    @abstractmethod
    async def extrair_noticias(self, limite: int = 10) -> list[Noticia]:
        """Extrai as ultimas `limite` noticias e retorna lista de Noticia."""
        ...


async def abrir_pagina(url: str) -> tuple[Playwright, Browser, Page]:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page(
        user_agent=USER_AGENT,
        viewport={"width": 1366, "height": 900},
        locale="pt-BR",
    )
    page.set_default_timeout(20_000)
    await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    await page.wait_for_timeout(2_500)
    return playwright, browser, page


async def fechar_pagina(playwright: Playwright, browser: Browser) -> None:
    await browser.close()
    await playwright.stop()


def _titulo_valido(titulo: str) -> bool:
    titulo = _limpar_texto(titulo)
    if len(titulo) < 18 or len(titulo) > 220:
        return False
    texto = titulo.lower()
    if any(term in texto for term in BLOCKED_TITLE_TERMS):
        return False
    return any(keyword in texto for keyword in NEWS_KEYWORDS)


def _limpar_texto(texto: str) -> str:
    texto = " ".join(str(texto or "").split())
    try:
        reparado = texto.encode("latin1").decode("utf-8")
    except UnicodeError:
        reparado = texto
    return reparado


async def coletar_links_noticias(
    page: Page,
    *,
    fonte: str,
    base_url: str,
    limite: int,
    url_deve_conter: list[str] | None = None,
) -> list[Noticia]:
    noticias: list[Noticia] = []
    vistos: set[str] = set()
    links = await page.locator("a[href]").all()

    for link in links:
        if len(noticias) >= limite:
            break
        try:
            href = await link.get_attribute("href")
            texto = " ".join((await link.inner_text()).split())
        except Exception:
            continue

        if not href or not texto:
            continue
        url = urljoin(base_url, href)
        if url in vistos:
            continue
        if any(term in url.lower() for term in BLOCKED_URL_TERMS):
            continue
        if url_deve_conter and not any(fragmento in url.lower() for fragmento in url_deve_conter):
            continue
        if not _titulo_valido(texto):
            continue

        vistos.add(url)
        noticias.append(
            Noticia(
                titulo=_limpar_texto(texto),
                data="",
                resumo="",
                url=url,
                fonte=fonte,
            )
        )

    return noticias
