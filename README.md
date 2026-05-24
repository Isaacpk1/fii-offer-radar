# BTG Scraper

Projeto em Python para extrair, processar, enriquecer e analisar ofertas primarias de Fundos de Investimento Imobiliario (FIIs) registradas na CVM pela Resolucao CVM 160. A base final cruza informacoes das ofertas com dados macroeconomicos, especialmente Selic, CDI, IPCA 12m, cambio USD/BRL e IFIX, e alimenta uma interface analitica em Streamlit com apoio de um agente de IA.

## Objetivo

O objetivo do projeto e permitir analises comparativas entre ofertas de FIIs, apoiando perguntas como:

- Quais coordenadores lideres concentram maior volume registrado?
- Como o volume de ofertas evolui ao longo do tempo?
- Como comparar ofertas por emissor, publico-alvo, status, Selic e IFIX?
- Como usar IA para consultar a base processada em linguagem natural?

## Tecnologias Utilizadas

| Tecnologia | Uso no projeto |
| --- | --- |
| Python | Linguagem principal do pipeline, processamento e aplicacao. |
| Pandas | Leitura, limpeza, transformacao e cruzamento das bases CSV. |
| Requests | Download dos dados oficiais da CVM e consulta da API do Banco Central. |
| bcb | Coleta de series SGS do Banco Central: Selic, CDI, IPCA 12m e USD/BRL. |
| yfinance | Obtencao do historico do IFIX. |
| Streamlit | Interface web interativa do dashboard. |
| streamlit-aggrid | Tabelas interativas com filtro por coluna, ordenacao, paginacao e selecao. |
| Plotly Express | Graficos de volume, ranking, dispersao e distribuicao. |
| Plotly Graph Objects | Graficos dual-axis com barras e linhas em eixos independentes. |
| LangChain | Criacao do agente analitico sobre o DataFrame. |
| Google Gemini | Modelo de IA usado pelo agente via `langchain-google-genai`. |
| Playwright | Estrutura para coleta configuravel de fontes complementares e monitoramento. |
| python-dotenv | Carregamento das variaveis de ambiente do arquivo `.env`. |

## Arquitetura do Projeto

O projeto segue um fluxo em camadas:

1. **Extracao**: baixa dados brutos da CVM, indicadores macro do BCB e IFIX.
2. **Processamento**: filtra ofertas de FIIs e padroniza colunas relevantes.
3. **Enriquecimento**: cruza ofertas com Selic, CDI, IPCA 12m, cambio e IFIX pela data de requerimento.
4. **Analise**: disponibiliza a base no dashboard, nas tabelas AgGrid e no agente de IA.

```text
btg_scraper/
|-- .env
|-- .gitignore
|-- LICENSE
|-- README.md
|-- requirements.txt
|-- src/
|   |-- main.py
|   |-- ai_core/
|   |   |-- agent.py
|   |   |-- tools.py
|   |-- data/
|   |   |-- raw/
|   |   |   |-- oferta_resolucao_160_bruto.csv
|   |   |   |-- macro_bcb_bruto.csv
|   |   |   |-- selic_bruto.csv
|   |   |   |-- ifix_bruto.csv
|   |   |-- processed/
|   |   |   |-- ofertas_fiis_pronto_para_ia.csv
|   |   |   |-- status_monitor_state.json
|   |   |   |-- status_monitor_alerts.json
|   |-- data_extraction/
|   |   |-- cvm_extractor.py
|   |   |-- macro_extractor.py
|   |   |-- anbima_extractor.py
|   |   |-- status_monitor.py
|   |-- data_processing/
|   |   |-- cleaner.py
|   |   |-- enricher.py
|   |-- frontend/
|   |   |-- app.py
|-- venv/
```

## Pastas e Arquivos

| Caminho | Funcao |
| --- | --- |
| `.env` | Armazena variaveis de ambiente, como `GOOGLE_API_KEY`. Nao deve ser publicado. |
| `.gitignore` | Ignora ambiente virtual, caches, logs e arquivos sensiveis. |
| `requirements.txt` | Lista as dependencias Python do projeto. |
| `src/main.py` | Orquestra o pipeline completo: extracao, limpeza e enriquecimento. |
| `src/data_extraction/cvm_extractor.py` | Baixa o ZIP de ofertas da CVM e salva a base bruta da Resolucao CVM 160. |
| `src/data_extraction/macro_extractor.py` | Baixa Selic, CDI, IPCA 12m e USD/BRL pelo Banco Central e IFIX via Yahoo Finance. |
| `src/data_extraction/anbima_extractor.py` | Estrutura Playwright configuravel para extrair tabelas publicas da ANBIMA quando houver URL e seletor real. |
| `src/data_extraction/status_monitor.py` | Compara status atuais das ofertas com um snapshot local e gera alertas para o dashboard. |
| `src/data_processing/cleaner.py` | Filtra apenas ofertas de FIIs e seleciona as colunas relevantes. |
| `src/data_processing/enricher.py` | Cruza ofertas com macro, IFIX e gera a base final processada. |
| `src/ai_core/agent.py` | Inicializa o agente LangChain/Gemini sobre a base final. |
| `src/ai_core/tools.py` | Tools do agente para macro atual, consulta de oferta CVM e spread contra CDI. |
| `src/frontend/app.py` | Dashboard Streamlit com filtros, rankings, comparacao de ofertas, base CVM e copiloto de IA. |
| `src/data/raw/` | Dados brutos baixados das fontes externas. |
| `src/data/processed/` | Dados prontos para analise e IA. |
| `venv/` | Ambiente virtual local. Nao faz parte do codigo-fonte. |

## Dados Gerados

| Arquivo | Descricao |
| --- | --- |
| `src/data/raw/oferta_resolucao_160_bruto.csv` | Base bruta de ofertas baixada da CVM. |
| `src/data/raw/macro_bcb_bruto.csv` | Series Selic, CDI, IPCA 12m e USD/BRL baixadas do Banco Central. |
| `src/data/raw/selic_bruto.csv` | Serie diaria da Selic obtida no Banco Central. |
| `src/data/raw/ifix_bruto.csv` | Historico do IFIX obtido via `yfinance`. |
| `src/data/processed/ofertas_fiis_pronto_para_ia.csv` | Base final com ofertas de FIIs enriquecidas com indicadores macro e IFIX. |
| `src/data/processed/status_monitor_state.json` | Snapshot local de status usado pelo monitor. |
| `src/data/processed/status_monitor_alerts.json` | Alertas de mudanca de status exibidos na sidebar. |

## Como Rodar

Crie e ative um ambiente virtual:

```bash
python -m venv venv
venv\Scripts\activate
```

Instale as dependencias:

```bash
pip install -r requirements.txt
```

Configure o arquivo `.env` com a chave do Gemini:

```env
GOOGLE_API_KEY=sua_chave_aqui
```

Execute o pipeline completo:

```bash
python src/main.py
```

Abra o dashboard:

```bash
streamlit run src/frontend/app.py
```

Rode o monitor de status:

```bash
python src/data_extraction/status_monitor.py
```

## Funcionalidades do Dashboard

- Filtros por periodo, coordenador lider, status e publico-alvo.
- Indicadores de volume total, quantidade de ofertas, ticket medio, Selic media e IFIX medio.
- Grafico dual-axis de volume mensal x Selic.
- Heatmap de correlacao entre volume, Selic, CDI, IPCA, cambio e IFIX.
- Aba Macro com series temporais comparativas.
- Distribuicao de volume por status e publico-alvo.
- Comparacao direta entre ofertas selecionadas.
- Ranking de coordenadores lideres com drill-down por selecao no AgGrid.
- Treemap coordenador -> emissor -> volume.
- Base CVM em AgGrid com filtro, ordenacao, paginacao, selecao e download do recorte filtrado.
- Copiloto de IA com memoria de conversa e tools customizadas.
- Botao para gerar relatorio executivo do recorte filtrado.

## Agente de IA

O agente usa Gemini via LangChain e possui:

- memoria de conversa na sessao do Streamlit;
- acesso ao CSV processado;
- tool `buscar_macro_atual` para Selic, CDI, IPCA 12m e USD/BRL;
- tool `consultar_oferta_cvm` para buscar uma oferta pelo numero do processo;
- tool `calcular_spread_cdi` para comparar uma taxa informada com o CDI atual.

## Playwright

As features Playwright foram implementadas como base configuravel:

- `anbima_extractor.py` recebe URL e seletor CSS da tabela a extrair, porque paginas da ANBIMA podem variar por fonte e layout.
- `status_monitor.py` monitora mudancas comparando o CSV processado atual com um snapshot salvo localmente.

Para coleta real, configure a URL e o seletor da tabela desejada no `anbima_extractor.py`.

## Limpeza Realizada

Foram removidos arquivos gerados e modulos que nao faziam parte do fluxo atual:

- `__pycache__/`: caches automaticos do Python.
- `src/data_extraction/bcb_extractor.py`: extrator legado que gerava arquivos em caminhos fora do padrao atual.
- `src/data_processing/data_processor.py`: processador legado que usava nomes de arquivos antigos e dados simulados para spread.

## Observacoes

- O dashboard nao usa dados mockados: ele le `src/data/processed/ofertas_fiis_pronto_para_ia.csv`.
- Se a base processada nao existir, rode `python src/main.py`.
- A disponibilidade historica do IFIX depende do retorno do Yahoo Finance para o ticker `IFIX.SA`.
- O arquivo `.env`, o `venv/` e os caches Python ficam fora do versionamento pelo `.gitignore`.
