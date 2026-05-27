# Aderencia ao Projeto TAPI - Ofertas Primarias de FIIs

Este documento registra a analise estatica do projeto em relacao ao PDF `TAPI - BTG (1).pdf`, mantendo o foco em ofertas primarias. Dados de Fundos Imobiliarios entram como suporte para decidir se uma emissao merece analise, comparacao ou monitoramento.

## Escopo Do PDF

O projeto TAPI pede um agente inteligente capaz de:

- coletar ofertas primarias de multiplas fontes;
- padronizar dados para comparacao;
- identificar diferencas relevantes entre ofertas similares;
- contextualizar variacoes com indicadores macroeconomicos e noticias;
- produzir relatorios analiticos quantitativos e interpretativos;
- disponibilizar uma interface interativa em Streamlit;
- documentar fontes, metodologia, modelos, resultados, limitacoes e evolucoes.

## Decisao De Foco

O produto principal nao e um screener completo de FIIs. O produto principal e uma mesa de inteligencia para ofertas primarias de FIIs.

Pergunta central:

```text
Esta oferta primaria faz sentido versus o fundo, a B3, o valor patrimonial, a liquidez e o cenario macro?
```

## Status Atual

| Requisito TAPI | Status | Evidencia no projeto |
| --- | --- | --- |
| Coleta automatizada | Implementado | `cvm_extractor.py`, `macro_extractor.py`, `fii_informe_extractor.py`, `fii_market_extractor.py`, `news/` |
| Padronizacao | Implementado | `cleaner.py`, `enricher.py`, `database/build_database.py`; `fii_analyzer.py` fica como export opcional |
| Base centralizada | Implementado | `src/data/processed/fii_warehouse.duckdb` |
| Comparacao entre ofertas | Implementado | `ofertas_cvm`, `oferta_inteligencia`, abas `Mercado`, `Ofertas` e `Tese da Oferta` |
| Tese por oferta primaria | Implementado | Score, sinais e ficha de decisao em `oferta_inteligencia` |
| Contexto macro | Implementado com ressalva | `macro_series`, Selic, CDI, IPCA e USD/BRL; IFIX depende da cobertura retornada pelo Yahoo Finance |
| Contexto informacional | Parcial | Scrapers de noticias existem, mas dependem da estabilidade dos sites |
| Suporte do fundo | Parcial | `fii_metricas`; melhora a leitura, mas nao bloqueia a tese da oferta |
| Relatorio interpretativo | Implementado | Copiloto LangChain/Gemini no dashboard |
| Interface interativa | Implementado | `src/frontend/app.py` |
| Documentacao | Implementado | `README.md`, `docs/DATABASE.md`, este documento |

## Tabelas Do Warehouse

| Tabela | Prontidao | Uso |
| --- | --- | --- |
| `dim_fii` | Boa | Cadastro de CNPJ, ticker e nome |
| `ofertas_cvm` | Boa | Base oficial das ofertas primarias |
| `oferta_inteligencia` | Boa | Tese da emissao: preco, B3, VP, liquidez, historico, macro, score e cobertura |
| `fii_informe_mensal` | Suporte parcial | PL, VP/C e cotistas quando a fonte tiver cobertura |
| `fii_cotacoes` | Suporte parcial | Preco e liquidez financeira para tickers mapeados com alta confianca |
| `fii_rendimentos` | Estrutura pronta | Aguardando extrator de dividendos |
| `fii_portfolio` | Estrutura pronta | Aguardando extrator/parser de relatorios gerenciais |
| `macro_series` | Boa para macro; parcial para IFIX | Selic, CDI, IPCA e USD/BRL com boa cobertura; IFIX depende da fonte |
| `fii_metricas` | Suporte parcial | Dados do fundo para enriquecer a tese da oferta |
| `data_quality_report` | Boa | Auditoria de cobertura das tabelas |

## O Que Ja Da Para Demonstrar

- ranking de ofertas por volume;
- ranking de coordenadores;
- ranking de priorizacao das ofertas;
- ficha de decisao por processo CVM;
- evolucao mensal de volume versus Selic/CDI;
- comparacao de preco de emissao contra preco B3 quando ha ticker mapeado;
- liquidez media dos FIIs mapeados;
- status e publico-alvo das ofertas;
- relatorio de cobertura mostrando o que ainda nao pode ser afirmado com seguranca.

## Lacunas Que Viraram Suporte

| Lacuna | Impacto na tese de oferta | Proxima acao |
| --- | --- | --- |
| Dividend Yield 12m | Melhora leitura de retorno, mas nao bloqueia comparacao emissao vs B3/macro | Criar `fii_dividends_extractor.py` |
| VP/C, PL e cotistas completos | Melhora comparacao contra patrimonio | Melhorar captura do informe geral CVM ou integrar API |
| Vacancia e imoveis | Melhora leitura de risco operacional | Criar `fii_reports_extractor.py` |
| Serie historica de cotacoes | Melhora analise de tendencia e volatilidade | Evoluir `fii_cotacoes` para historico diario |

## Conclusao

O projeto esta aderente ao escopo TAPI para ofertas primarias de FIIs. A analise fundamentalista completa do fundo fica como camada de suporte: melhora a decisao, mas nao e o produto principal.
