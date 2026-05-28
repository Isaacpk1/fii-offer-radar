# BTG Scraper

Pipeline, warehouse, dashboard e agente de IA para triagem de ofertas primarias de FIIs da Resolucao CVM 160.

O projeto centraliza dados oficiais da CVM, macroeconomia, informes mensais de FIIs, mercado secundario quando existe ticker mapeado, documentos de oferta, noticias e um copiloto analitico. Ele serve para priorizar analises, nao para substituir decisao de investimento.

## Principais Entregas

- Ofertas primarias de FIIs registradas na CVM.
- Enriquecimento macro por data da oferta: Selic, CDI, IPCA 12m, USD/BRL e IFIX quando disponivel.
- Informe mensal de FIIs com VP/C, patrimonio, cotistas e metricas operacionais conforme cobertura da CVM.
- Mapeamento CNPJ -> ticker com cache para buscar preco e liquidez B3 quando possivel.
- Documentos de oferta: manifesto, download, parsing deterministico e extracao via LLM.
- DY historico sobre preco de emissao e DY projetado quando encontrado em documentos.
- Warehouse DuckDB com tabela principal `oferta_inteligencia`.
- Score de priorizacao e sistema auditavel de confianca por oferta.
- Dashboard Streamlit com abas de tese, mercado, ofertas, suporte FII, qualidade, tabelas e copiloto.
- Agente LangChain/Gemini com tools de ranking, tese, noticias, qualidade, macro, brief e registro de decisao.

## Limites Importantes

- Preco B3, P/VP de mercado e liquidez so existem quando o ticker foi mapeado e a coleta de mercado funcionou.
- Fundos sem B3 ainda podem ter dados uteis: VP/C, patrimonio, cotistas, rendimento historico e historico de ofertas.
- DY projetado e dado prospectivo do emissor/documento de oferta, nao dado auditado.
- Noticias sao contexto qualitativo best effort; sites podem bloquear scraping ou mudar layout.
- O runner autonomo e manual/agendavel; nao roda como servico continuo por padrao.
- `yfinance` atende prototipo/triagem, mas nao substitui fonte institucional de mercado.

## Estrutura De Pastas

```text
.
|-- docs/
|   |-- DATABASE.md
|   |-- FILE_INVENTORY.md
|   `-- PRODUCT_SCOPE.md
|-- src/
|   |-- main.py
|   |-- ai_core/
|   |   |-- agent.py
|   |   |-- autonomous_runner.py
|   |   |-- macro.py
|   |   |-- schemas.py
|   |   |-- tool_config.py
|   |   |-- tools.py
|   |   |-- tools_confidence.py
|   |   |-- tools_ranking.py
|   |   |-- tools_read.py
|   |   |-- tools_write.py
|   |   `-- warehouse.py
|   |-- data/
|   |   |-- raw/
|   |   |-- processed/
|   |   |-- alertas_autonomos/
|   |   `-- briefs/
|   |-- data_extraction/
|   |   |-- cvm_extractor.py
|   |   |-- fii_informe_extractor.py
|   |   |-- fii_market_extractor.py
|   |   |-- fii_ticker_mapper.py
|   |   |-- macro_extractor.py
|   |   |-- status_monitor.py
|   |   |-- oferta_document_*.py
|   |   `-- news/
|   |       |-- b3_news.py
|   |       |-- base_scraper.py
|   |       |-- funds_explorer.py
|   |       |-- infomoney.py
|   |       |-- news_aggregator.py
|   |       `-- valor_economico.py
|   |-- data_processing/
|   |   |-- cleaner.py
|   |   |-- confidence_scorer.py
|   |   |-- enricher.py
|   |   `-- utils.py
|   |-- database/
|   |   |-- schema.sql
|   |   |-- build_common.py
|   |   |-- build_database.py
|   |   |-- builders.py
|   |   |-- *_builders.py
|   |   `-- quality.py
|   `-- frontend/
|       |-- app.py
|       |-- agent_session.py
|       |-- components.py
|       |-- config.py
|       |-- data.py
|       |-- formatters.py
|       |-- styles.py
|       |-- view_utils.py
|       |-- views.py
|       `-- views_*.py
|-- pyproject.toml
|-- requirements.txt
`-- README.md
```

`src/data/` contem artefatos gerados localmente e fica fora do git.

## Tecnologias Usadas

| Area | Tecnologias |
| --- | --- |
| Linguagem | Python 3.11+ |
| Dados/tabular | pandas, numpy |
| Warehouse | DuckDB, SQL |
| Extracao HTTP | requests |
| Mercado | yfinance |
| Macro Brasil | python-bcb / SGS Banco Central |
| Scraping JS | Playwright / Chromium |
| PDF/documentos | pypdf |
| Frontend | Streamlit |
| Tabelas interativas | streamlit-aggrid, fallback para `st.dataframe` |
| Graficos | Plotly Express, Plotly Graph Objects |
| IA/agentes | LangChain, LangChain Classic, LangChain Experimental |
| LLM | Google Gemini via `langchain-google-genai` |
| Schemas/validacao | Pydantic |
| Config local | python-dotenv, `.env` |
| Packaging local | pyproject.toml, setuptools, `pip install -e .` |
| Utilitario do agente Pandas | tabulate |
| Automacao manual/agendada | `src/main.py`, `autonomous_runner.py`, Task Scheduler/cron |

## Instalacao

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
playwright install chromium
```

Crie `.env` na raiz:

```env
GOOGLE_API_KEY=sua_chave
GEMINI_MODEL=gemini-2.5-flash
AGENT_VERBOSE=false

# Opcional: envio de alertas por e-mail no autonomous_runner.py
SMTP_HOST=smtp.seuprovedor.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_FROM=alertas@empresa.com
SMTP_USERNAME=alertas@empresa.com
SMTP_PASSWORD=sua_senha_ou_app_password
ALERT_EMAIL_TO=analista@empresa.com
```

## Execucao

Pipeline completo:

```powershell
.\venv\Scripts\python.exe src/main.py
```

Forcar nova coleta:

```powershell
.\venv\Scripts\python.exe src/main.py --force
```

Reconstruir apenas o warehouse:

```powershell
.\venv\Scripts\python.exe src/database/build_database.py
```

Coletar noticias via Playwright:

```powershell
.\venv\Scripts\python.exe -m data_extraction.news.news_aggregator
```

Frontend:

```powershell
.\venv\Scripts\streamlit.exe run src/frontend/app.py
```

Runner autonomo manual/agendavel:

```powershell
.\venv\Scripts\python.exe src/ai_core/autonomous_runner.py
```

Runner com e-mail, se SMTP estiver configurado:

```powershell
.\venv\Scripts\python.exe src/ai_core/autonomous_runner.py --send-email
```

Runner em loop local:

```powershell
.\venv\Scripts\python.exe src/ai_core/autonomous_runner.py --loop --interval-minutes 1440 --send-email
```

Exemplo de cron em Linux:

```cron
0 7 * * 1-5 cd /caminho/btg_scraper && .venv/bin/python src/ai_core/autonomous_runner.py --send-email
```

No Windows, configure o Task Scheduler para executar:

```text
Programa: C:\caminho\btg_scraper\venv\Scripts\python.exe
Argumentos: src/ai_core/autonomous_runner.py --send-email
Iniciar em: C:\caminho\btg_scraper
```

## Fluxo Do Pipeline

1. Baixa ofertas CVM 160, macro BCB e IFIX.
2. Baixa informe mensal de FIIs do ano atual.
3. Coleta noticias best effort via Playwright.
4. Limpa e filtra ofertas de cotas de FII.
5. Enriquece ofertas com macro e IFIX pela data.
6. Verifica mudancas de status.
7. Mapeia ticker por CNPJ e busca mercado B3 quando possivel.
8. Consolida documentos, DY projetado/historico, score e confianca.
9. Gera `src/data/processed/fii_warehouse.duckdb`.

## Principais Tabelas

| Tabela | Uso |
| --- | --- |
| `ofertas_cvm` | Ofertas primarias, status, volumes, coordenadores e macro. |
| `dim_fii` | Cadastro consolidado por CNPJ/ticker. |
| `fii_informe_mensal` | VP/C, PL, cotistas e dados operacionais quando disponiveis. |
| `fii_cotacoes` | Preco e liquidez para tickers mapeados. |
| `fii_metricas` | Suporte do fundo para a tese da oferta. |
| `oferta_projecoes` | DY projetado/historico e fontes documentais. |
| `oferta_inteligencia` | Tese final por processo CVM. |
| `noticias_fiis` | Noticias coletadas para contexto qualitativo. |
| `data_quality_report` | Cobertura de dados por tabela/coluna. |

## Documentacao Complementar

- `docs/DATABASE.md`: warehouse, tabelas e cobertura.
- `docs/PRODUCT_SCOPE.md`: escopo do produto, limites e features reais.
- `docs/FILE_INVENTORY.md`: inventario de arquivos e artefatos.

## Exemplo DuckDB

```python
import duckdb

con = duckdb.connect("src/data/processed/fii_warehouse.duckdb")
df = con.execute("""
    SELECT numero_processo, ticker, nome_emissor, preco_emissao,
           valor_cota_vpc, p_vp_emissao, preco_cota_b3,
           desconto_vs_b3, confianca_total, score_priorizacao
    FROM oferta_inteligencia
    ORDER BY score_priorizacao DESC NULLS LAST
    LIMIT 20
""").df()
```

## Manutencao

- Pare o Streamlit antes de reconstruir o DuckDB se houver lock de arquivo.
- Rode `src/database/build_database.py` quando schema ou builders mudarem.
- Use `src/main.py --force` quando quiser atualizar fontes externas.
- Reinstale browsers com `playwright install chromium` se os scrapers de noticias falharem por browser ausente.
- O agente executa codigo Pandas via LangChain com `allow_dangerous_code=True`; use em ambiente controlado.
