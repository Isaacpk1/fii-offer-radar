# Base Analitica de FIIs

Este documento descreve como montar a base de dados necessaria para comparar FIIs e ofertas primarias com as metricas do material `Analise de FII`.

## Objetivo

Criar um warehouse local em DuckDB para centralizar:

- dados oficiais de ofertas CVM 160;
- informes mensais de FIIs;
- cotacoes e liquidez de mercado;
- series macroeconomicas;
- rendimentos e dividend yield;
- portfolio, vacancia e custos;
- metricas calculadas para comparacao.

O arquivo gerado fica em:

```text
src/data/processed/fii_warehouse.duckdb
```

## Fontes

| Tema | Fonte preferencial | Status no projeto |
| --- | --- | --- |
| Ofertas primarias | CVM dados abertos, Resolucao CVM 160 | Implementado |
| Status, volume e coordenador | CVM dados abertos | Implementado |
| Selic, CDI, IPCA, USD/BRL | Banco Central SGS via `python-bcb` | Implementado |
| IFIX | Yahoo Finance via `yfinance` | Parcial: fonte retorna cobertura limitada neste ambiente |
| Informe mensal FII | CVM dados abertos, Informe Mensal Estruturado | Implementado parcialmente |
| Preco e volume B3 | B3 oficial, Brapi, Partnr ou yfinance | Implementado parcialmente via yfinance |
| Rendimentos e DY | CVM Informe Mensal; prospectos/estudos para DY projetado | Parcial: historico estimado implementado; DY projetado depende de documentos |
| Vacancia e portfolio | Relatorios gerenciais/CVM, Brapi ou Partnr | Pendente |
| Noticias | InfoMoney, Valor, Funds Explorer, B3 | Implementado como scraping best effort |

## Camadas

### Raw

Arquivos exatamente como chegam das fontes externas.

```text
src/data/raw/
```

Exemplos:

- `oferta_resolucao_160_bruto.csv`
- `macro_bcb_bruto.csv`
- `ifix_bruto.csv`
- `informe_mensal_fii_<ano>.csv`
- `fii_mercado_bruto.csv`

### Processed

Arquivos tratados para consumo pelo dashboard, agente e warehouse.

```text
src/data/processed/
```

Exemplos:

- `ofertas_fiis_pronto_para_ia.csv`
- `fii_analise_completa.csv` (export opcional; o warehouse calcula as metricas diretamente)
- `fii_warehouse.duckdb`

### Warehouse

Banco DuckDB gerado por:

```bash
python src/database/build_database.py
```

## Tabelas

### `dim_fii`

Cadastro consolidado dos fundos.

Campos principais:

- `cnpj`
- `ticker`
- `nome`
- `administrador`
- `gestor`
- `segmento`
- `tipo_fii`

Uso: base para joins e filtros por fundo.

### `ofertas_cvm`

Ofertas primarias de FIIs registradas na CVM.

Campos principais:

- `numero_processo`
- `cnpj_emissor`
- `nome_emissor`
- `nome_lider`
- `data_requerimento`
- `status_requerimento`
- `tipo_oferta`
- `valor_total_registrado`
- `preco_emissao`
- `taxa_selic_data_oferta`
- `pontos_ifix_data_oferta`

Uso: comparar emissoes, coordenadores, volumes, status e contexto macro.

### `fii_informe_mensal`

Indicadores periodicos enviados pelos FIIs.

Campos principais:

- `cnpj`
- `competencia`
- `patrimonio_liquido`
- `valor_cota_vpc`
- `numero_cotistas`
- `total_ativos`
- `total_passivo`
- `taxa_administracao`
- `taxa_gestao`

Uso: calcular VP/C, P/VP, porte, custos e qualidade patrimonial.

Observacao: se a CVM entregar apenas arquivos de ativos, alguns campos ficam sem cobertura. O relatorio `data_quality_report` mostra isso.

### `fii_cotacoes`

Preco e liquidez de mercado.

Campos principais:

- `ticker`
- `data`
- `preco_fechamento`
- `volume_financeiro`
- `volume_medio_diario`

Uso: comparar preco de mercado com preco de emissao e calcular liquidez.

### `fii_rendimentos`

Rendimentos mensais estimados a partir do informe mensal da CVM.

Campos principais:

- `ticker`
- `cnpj`
- `data_com`
- `data_pagamento`
- `rendimento_por_cota`
- `valor_cota_base`
- `dividend_yield_mes`
- `dividend_yield_12m`
- `metodo_estimativa`

Observacao: `rendimento_por_cota` e estimado por `Dividend_Yield_Mes x Valor_Cota_VPC`. Isso serve como historico auditavel, mas nao substitui o rendimento projetado oficial da oferta.

### `fii_portfolio`

Tabela preparada para operacao e portfolio.

Campos principais:

- `cnpj`
- `competencia`
- `numero_imoveis`
- `vacancia_fisica`
- `vacancia_financeira`
- `perfil_inquilinos`
- `exposicao_imoveis`
- `exposicao_cri`
- `exposicao_fii`

Status: pendente de extrator/API ou parser de relatorios gerenciais.

### `macro_series`

Series macroeconomicas por data.

Campos principais:

- `data`
- `taxa_selic`
- `ipca_12m`
- `cdi`
- `usd_brl`
- `ifix`

Uso: explicar janelas de mercado e comparar ofertas por cenario macro.

### `fii_metricas`

Tabela final de comparacao por fundo.

Campos principais:

- `cnpj`
- `ticker`
- `patrimonio_liquido`
- `valor_cota_vpc`
- `preco_cota`
- `p_vp`
- `preco_emissao`
- `desconto_oferta_vp`
- `desconto_oferta_b3`
- `volume_medio_diario`
- `total_emissoes`
- `volume_total_ofertas`
- `coordenador_principal`
- `dividend_yield_12m`

Uso: tela de comparacao de FIIs e ranking de oportunidades.

### `oferta_projecoes`

Tabela que separa o historico calculado do que deve vir do prospecto/estudo de viabilidade.

Campos principais:

- `numero_processo`
- `preco_emissao`
- `rendimento_12m_historico_por_cota`
- `meses_historico_utilizados`
- `dy_12m_historico_sobre_emissao`
- `dy_projetado_oferta`
- `rendimento_anual_projetado_por_cota`
- `documento_url`
- `documento_path`
- `fonte_trecho`
- `confianca_extracao`

Uso: comparar a oferta pelo preco de emissao usando historico CVM e receber, depois, o DY projetado extraido de prospectos com Playwright + parser/IA.

### `oferta_inteligencia`

Tabela principal para o foco atual do projeto: avaliar ofertas primarias.

Campos principais:

- `numero_processo`
- `ticker`
- `preco_emissao`
- `dy_12m_historico_sobre_emissao`
- `dy_projetado_oferta`
- `preco_cota_b3`
- `valor_cota_vpc`
- `desconto_vs_b3`
- `desconto_vs_vp`
- `p_vp_emissao`
- `liquidez_sobre_oferta`
- `sinal_preco_b3`
- `sinal_preco_vp`
- `sinal_liquidez`
- `sinal_historico`
- `score_priorizacao`
- `leitura_priorizacao`
- `cobertura_analise_percentual`

Uso: ranquear quais emissoes merecem analise primeiro, sem transformar o app em um screener generico de FIIs.

### `data_quality_report`

Relatorio automatico de cobertura por tabela e coluna.

Campos principais:

- `tabela`
- `coluna`
- `total_linhas`
- `valores_preenchidos`
- `cobertura_percentual`
- `observacao`

Uso: saber exatamente quais comparacoes ja sao confiaveis e quais ainda precisam de fonte.

## Comparacoes Do PDF

| Comparacao | Tabela | Campo/Formula | Status |
| --- | --- | --- | --- |
| Preco da cota | `oferta_inteligencia` | `preco_cota_b3` | Suporte quando ha ticker confiavel |
| VP/C | `oferta_inteligencia` | `valor_cota_vpc` | Suporte quando ha informe geral |
| P/VP de mercado | `oferta_inteligencia` | `p_vp` | Suporte quando ha ticker confiavel e preco B3 |
| P/VP da emissao | `oferta_inteligencia` | `p_vp_emissao` | Implementado quando ha VP/C |
| Patrimonio liquido | `oferta_inteligencia` | `patrimonio_liquido` | Suporte quando ha informe geral |
| Dividend Yield 12m historico | `oferta_projecoes` / `oferta_inteligencia` | soma 12m de rendimento estimado / `preco_emissao` | Implementado como baseline CVM |
| DY projetado da oferta | `oferta_projecoes` / `oferta_inteligencia` | extraido do prospecto/estudo de viabilidade | Estrutura pronta; parser pendente |
| Rendimento por cota | `fii_rendimentos` | `Dividend_Yield_Mes x Valor_Cota_VPC` | Implementado como estimativa CVM |
| Historico de pagamentos | `fii_rendimentos` | serie temporal mensal estimada | Implementado como estimativa CVM |
| Vacancia | `fii_portfolio` | `vacancia_fisica`, `vacancia_financeira` | Pendente |
| Numero de imoveis | `fii_portfolio` | `numero_imoveis` | Pendente |
| Taxas | `fii_informe_mensal` | `taxa_administracao`, `taxa_gestao` | Depende da fonte |
| Liquidez diaria | `oferta_inteligencia` | `volume_medio_diario`, `liquidez_sobre_oferta` | Volume financeiro medio; suporte quando ha ticker confiavel |
| Preco de emissao | `oferta_inteligencia` | `preco_emissao` | Implementado |
| Desconto sobre VP | `oferta_inteligencia` | `desconto_vs_vp`, `p_vp_emissao` | Implementado quando ha VP/C |
| Desconto contra B3 | `oferta_inteligencia` | `desconto_vs_b3` | Suporte quando ha ticker |
| Priorizacao da oferta | `oferta_inteligencia` | `score_priorizacao`, `leitura_priorizacao` | Implementado |

## Como Consultar

Exemplo em Python:

```python
import duckdb

con = duckdb.connect("src/data/processed/fii_warehouse.duckdb")
df = con.execute("""
    SELECT numero_processo, ticker, preco_emissao, preco_cota_b3,
           desconto_vs_b3, score_priorizacao, leitura_priorizacao
    FROM oferta_inteligencia
    ORDER BY score_priorizacao DESC
""").df()
```

Exemplo no terminal:

```bash
python src/database/build_database.py
```

## Proximos Extratores

Prioridade recomendada:

1. `fii_dividends_extractor.py`
   - substituir ou validar a estimativa CVM com fonte oficial de pagamentos;
   - recalcular `dividend_yield_12m`.

2. `oferta_document_manifest.py` + Playwright/parser de PDF
   - gerar a fila de prospectos pendentes;
   - baixar prospectos/estudos de viabilidade;
   - preencher `dy_projetado_oferta`, `rendimento_anual_projetado_por_cota`, `fonte_trecho` e `confianca_extracao`.

   O primeiro passo automatizado esta em `src/data_extraction/oferta_document_downloader.py`:

   ```bash
   python src/data_extraction/oferta_document_downloader.py --limite 10
   ```

   Ele le `oferta_documentos_manifest.csv`, busca PDFs candidatos, salva arquivos em `src/data/raw/oferta_documentos/` e gera `oferta_documentos_catalogo.csv` com URL, tipo, hash, tamanho e confianca do documento.

3. `fii_reports_extractor.py`
   - preencher `fii_portfolio`;
   - capturar vacancia, numero de imoveis, perfil de inquilinos e composicao da carteira.

4. Melhorar `fii_market_extractor.py`
   - trocar ou complementar `yfinance` por B3/Brapi/Partnr;
   - carregar serie historica diaria em `fii_cotacoes`, nao apenas o ultimo preco.

5. Melhorar `fii_informe_extractor.py`
   - garantir captura das tabelas gerais do informe CVM;
   - validar cobertura de PL, VP/C e cotistas no `data_quality_report`.
