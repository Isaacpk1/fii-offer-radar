from abc import ABC, abstractmethod
from dataclasses import dataclass


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