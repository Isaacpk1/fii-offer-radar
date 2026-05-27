# BTG Scraper

Pipeline em Python para acompanhar ofertas primarias de FIIs da Resolucao CVM 160, enriquecer os dados com cenario macroeconomico, comparar fundos listados e apoiar analises via dashboard Streamlit e agente de IA.

## O que o projeto entrega

- Base de ofertas de FIIs registradas na CVM.
- Indicadores macro por data da oferta: Selic, CDI, IPCA 12m, USD/BRL e IFIX quando a fonte tiver historico disponivel.
- Monitor de mudancas de status das ofertas.
- Informe mensal de FIIs com patrimonio, valor patrimonial por cota, cotistas e metricas operacionais quando disponiveis.
- Dados de mercado via Yahoo Finance para fundos com ticker mapeado com alta confianca.
- Base consolidada para comparar preco de emissao, preco de mercado, P/VP, liquidez e historico de ofertas.
- Warehouse local DuckDB para consultas analiticas e controle de cobertura dos dados.
- Dashboard Streamlit com filtros, rankings, graficos e copiloto de IA.

## Estrutura

```text
src/
  main.py                         Orquestra o pipeline completo
  ai_core/
    agent.py                      Agente LangChain/Gemini sobre a base processada
    tools.py                      Ferramentas auxiliares do agente
  data/
    raw/                          Arquivos brutos baixados das fontes externas
    processed/                    Bases finais consumidas pelo app e pela IA
  data_extraction/
    cvm_extractor.py              Ofertas CVM 160
    macro_extractor.py            Selic, CDI, IPCA, dolar e IFIX best effort
    fii_informe_extractor.py      Informe mensal CVM de FIIs
    fii_market_extractor.py       Preco e volume financeiro via yfinance
    status_monitor.py             Snapshot e alertas de status
    news/                         Scrapers de noticias de FIIs
  data_processing/
    cleaner.py                    Filtra ofertas de FIIs
    enricher.py                   Cruza ofertas com macro e IFIX
    fii_analyzer.py               Export opcional CSV de comparacao de FIIs
  database/
    schema.sql                    Modelo relacional do warehouse
    build_database.py             Gera src/data/processed/fii_warehouse.duckdb
  frontend/
    app.py                        Dashboard Streamlit
```

## Bases geradas

| Arquivo | Conteudo |
| --- | --- |
| `src/data/raw/oferta_resolucao_160_bruto.csv` | Base bruta de ofertas da CVM. |
| `src/data/raw/macro_bcb_bruto.csv` | Series do Banco Central usadas no enriquecimento. |
| `src/data/raw/ifix_bruto.csv` | IFIX via Yahoo Finance, quando a fonte retornar historico. |
| `src/data/raw/informe_mensal_fii_<ano>.csv` | Informe mensal consolidado de FIIs. |
| `src/data/raw/fii_mercado_bruto.csv` | Ticker, preco e volume medio dos FIIs mapeados. |
| `src/data/processed/ofertas_fiis_pronto_para_ia.csv` | Base principal de ofertas para dashboard e IA. |
| `src/data/processed/fii_analise_completa.csv` | Export opcional de comparacao de fundos, mercado e historico de emissoes. |
| `src/data/processed/fii_warehouse.duckdb` | Banco analitico local com dimensoes, fatos, metricas e qualidade. |
| `src/data/processed/status_monitor_alerts.json` | Mudancas de status detectadas na ultima execucao. |

## Instalacao

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Crie um arquivo `.env` na raiz com a chave do Gemini, se for usar o copiloto:

```env
GOOGLE_API_KEY=sua_chave
```

## Como executar

Pipeline completo:

```bash
python src/main.py
```

Dashboard:

```bash
streamlit run src/frontend/app.py
```

Etapas isoladas:

```bash
python src/data_extraction/cvm_extractor.py
python src/data_extraction/macro_extractor.py
python src/data_extraction/fii_informe_extractor.py
python src/data_processing/fii_analyzer.py
python src/database/build_database.py
```

## Fluxo do pipeline

1. Baixa ofertas CVM 160, indicadores macro e IFIX.
2. Baixa o informe mensal de FIIs do ano atual.
3. Coleta noticias de FIIs quando os scrapers conseguem acessar as fontes.
4. Filtra as ofertas cujo valor mobiliario e `Cotas de FII`.
5. Cruza as ofertas com indicadores macro e IFIX pela data de requerimento.
6. Busca dados de mercado dos FIIs com ticker conhecido.
7. Consolida a analise dos fundos com P/VP, preco de emissao, liquidez e historico de ofertas.
8. Gera o warehouse DuckDB em `src/data/processed/fii_warehouse.duckdb`.
9. Atualiza o monitor de mudancas de status.

## Warehouse DuckDB

O warehouse organiza os CSVs em tabelas analiticas:

| Tabela | Finalidade |
| --- | --- |
| `dim_fii` | Cadastro consolidado de fundos por CNPJ/ticker. |
| `ofertas_cvm` | Ofertas primarias, status, volumes, coordenadores e macro na data da oferta. |
| `fii_informe_mensal` | PL, VP/C, cotistas, ativos, passivos e taxas quando disponiveis. |
| `fii_cotacoes` | Preco e liquidez financeira de mercado. |
| `fii_rendimentos` | Estrutura preparada para dividendos e DY. |
| `fii_portfolio` | Estrutura preparada para vacancia, imoveis e composicao de carteira. |
| `macro_series` | Selic, CDI, IPCA, dolar e IFIX por data. |
| `oferta_inteligencia` | Tese por oferta primaria: emissao vs B3, VP, liquidez, historico, macro e score. |
| `fii_metricas` | Tabela final para comparacao de FIIs e ofertas. |
| `data_quality_report` | Cobertura de dados por tabela e coluna. |

Documentacao detalhada: `docs/DATABASE.md`.
Analise de aderencia ao escopo TAPI: `docs/TAPI_ALIGNMENT.md`.
Inventario de arquivos e criterio de limpeza: `docs/FILE_INVENTORY.md`.

Exemplo de consulta:

```python
import duckdb

con = duckdb.connect("src/data/processed/fii_warehouse.duckdb")
df = con.execute("""
    SELECT numero_processo, ticker, preco_emissao, valor_cota_vpc,
           p_vp_emissao, preco_cota_b3, desconto_vs_b3,
           score_priorizacao, leitura_priorizacao
    FROM oferta_inteligencia
    ORDER BY score_priorizacao DESC
""").df()
```

## Observacoes

- Os scrapers de noticias dependem de Playwright e podem falhar quando os sites alteram layout, bloqueiam automacao ou exigem assinatura.
- O mapeamento de tickers em `fii_market_extractor.py` e conservador: o codigo evita inventar tickers quando nao encontra correspondencia confiavel.
- As bases em `src/data/` sao artefatos gerados pelo pipeline. Rode novamente o pipeline para atualizar o dashboard.
- O agente de IA usa primeiro o warehouse `oferta_inteligencia` e ferramentas de ranking, tese da oferta, qualidade da base e macro. Ele executa codigo Pandas via LangChain; use apenas em ambiente controlado.
