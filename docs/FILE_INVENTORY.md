# Inventario De Arquivos

Este documento separa codigo-fonte, documentacao e artefatos gerados. A regra geral do projeto agora e: codigo e docs ficam versionados; dados baixados/processados ficam locais e sao regenerados pelo pipeline.

## Raiz

| Caminho | Status | Uso |
| --- | --- | --- |
| `.env` | Local | Chaves e configuracoes sensiveis. Nao versionar. |
| `.gitignore` | Essencial | Ignora ambiente virtual, cache, logs e dados gerados. |
| `LICENSE` | Essencial | Licenca do projeto. |
| `README.md` | Essencial | Guia principal de instalacao, execucao e arquitetura. |
| `requirements.txt` | Essencial | Dependencias Python. |
| `pyproject.toml` | Essencial | Configura o projeto como pacote instalavel em modo editavel. |

## Documentacao

| Caminho | Status | Uso |
| --- | --- | --- |
| `docs/DATABASE.md` | Essencial | Modelo do warehouse DuckDB, tabelas e fontes. |
| `docs/PRODUCT_SCOPE.md` | Essencial | Escopo real do produto, limites, abas e automacoes. |
| `docs/FILE_INVENTORY.md` | Essencial | Este inventario de limpeza e utilidade dos arquivos. |

## Codigo Fonte

| Caminho | Status | Uso |
| --- | --- | --- |
| `src/main.py` | Essencial | Orquestra o pipeline completo. |
| `src/ai_core/agent.py` | Essencial | Inicializa o agente LangChain/Gemini com contexto do warehouse e da tese de ofertas. |
| `src/ai_core/tools.py` | Essencial | Fachada das ferramentas do agente. |
| `src/ai_core/tools_read.py` | Essencial | Tools de consulta: tese, noticias, macro, qualidade e mercado agregado. |
| `src/ai_core/tools_ranking.py` | Essencial | Tools de ranking e output estruturado. |
| `src/ai_core/tools_write.py` | Util | Briefs e registro de decisoes. |
| `src/ai_core/tools_confidence.py` | Essencial | Avaliacao auditavel de confianca por oferta. |
| `src/ai_core/autonomous_runner.py` | Util | Runner manual/agendavel de alertas; suporta loop local e e-mail via SMTP opcional. |
| `src/data_extraction/cvm_extractor.py` | Essencial | Baixa ofertas CVM 160. |
| `src/data_extraction/macro_extractor.py` | Essencial | Baixa Selic, CDI, IPCA, USD/BRL e IFIX. |
| `src/data_extraction/fii_informe_extractor.py` | Essencial | Baixa informe mensal FII, incluindo VP/C, PL e cotistas via complemento CVM. |
| `src/data_extraction/fii_market_extractor.py` | Essencial | Busca preco e liquidez dos FIIs mapeados. |
| `src/data_extraction/fii_ticker_mapper.py` | Essencial | Mapeia CNPJ para ticker com cache. |
| `src/data_extraction/status_monitor.py` | Essencial | Detecta mudancas de status das ofertas. |
| `src/data_extraction/oferta_document_*.py` | Essencial | Manifesto, download e extracao de documentos de oferta. |
| `src/data_extraction/news/` | Util | Scrapers best effort de noticias; usados pelo pipeline, mas podem falhar por layout/bloqueio dos sites. |
| `src/data_processing/cleaner.py` | Essencial | Filtra ofertas de FIIs da base CVM. |
| `src/data_processing/enricher.py` | Essencial | Cruza ofertas com macro, IFIX e historico de status. |
| `src/database/schema.sql` | Essencial | Schema do warehouse. |
| `src/database/build_database.py` | Essencial | Gera `fii_warehouse.duckdb`, incluindo `oferta_inteligencia`. |
| `src/database/*_builders.py` | Essencial | Builders modulares do warehouse por dominio. |
| `src/database/__init__.py` | Essencial | Marca `database` como pacote Python. |
| `src/frontend/app.py` | Essencial | Dashboard Streamlit focado em ofertas primarias. |
| `src/frontend/views_*.py` | Essencial | Abas do dashboard: tese, mercado, ofertas, suporte FII, qualidade e copiloto. |

## Dados E Artefatos Gerados

Estes arquivos sao uteis localmente, mas nao devem ser versionados.

| Caminho | Gerado por | Uso |
| --- | --- | --- |
| `src/data/raw/oferta_resolucao_160_bruto.csv` | `cvm_extractor.py` | Fonte bruta de ofertas CVM. |
| `src/data/raw/macro_bcb_bruto.csv` | `macro_extractor.py` | Series macro principais. |
| `src/data/raw/ifix_bruto.csv` | `macro_extractor.py` | Historico IFIX. |
| `src/data/raw/informe_mensal_fii_<ano>.csv` | `fii_informe_extractor.py` | Informe mensal consolidado de FIIs. |
| `src/data/raw/fii_mercado_bruto.csv` | `fii_market_extractor.py` | Preco e liquidez dos tickers mapeados. |
| `src/data/processed/ofertas_fiis_pronto_para_ia.csv` | `enricher.py` | Base processada para dashboard e agente. |
| `src/data/processed/fii_warehouse.duckdb` | `build_database.py` | Banco analitico local. |
| `src/data/processed/noticias_fiis.json` | `news_aggregator.py` | Noticias coletadas. |
| `src/data/processed/status_monitor_*.json` | `status_monitor.py` | Estado e alertas de status. |
| `src/data/alertas_autonomos/*.json` | `autonomous_runner.py` | Alertas gerados quando o runner e executado manualmente/agendado. |

## Arquivos Removidos

| Caminho | Motivo |
| --- | --- |
| `btg_scraper_features.md` | Documento antigo, desatualizado e com encoding quebrado. |
| `src/data_extraction/anbima_extractor.py` | Extrator legado/removido; nao faz parte do fluxo atual. |
| `src/frontend/views_tapi.py` | Aba removida; nao havia regra de negocio util para o produto atual. |
| `streamlit.out.log`, `streamlit.err.log` | Logs vazios gerados em teste local. |
| `src/**/__pycache__/` | Cache Python gerado automaticamente. |

## Convencao De Nomes

- Extratores: `*_extractor.py`
- Processadores: nomes de acao/etapa, como `cleaner.py` e `enricher.py`.
- Banco: `src/database/schema.sql` e `src/database/build_database.py`
- Dados brutos: `src/data/raw/*_bruto.csv`
- Dados finais: `src/data/processed/*`
- Tabela principal para decisao: `oferta_inteligencia`
