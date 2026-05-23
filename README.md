# BTG Scraper

Projeto em Python para extrair, processar, enriquecer e analisar ofertas primarias de Fundos de Investimento Imobiliario (FIIs) registradas na CVM pela Resolucao CVM 160. A base final cruza informacoes das ofertas com dados macroeconomicos, especialmente Selic e IFIX, e alimenta uma interface analitica em Streamlit com apoio de um agente de IA.

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
| yfinance | Obtencao do historico do IFIX. |
| Streamlit | Interface web interativa do dashboard. |
| Plotly Express | Graficos de volume, ranking, dispersao e distribuicao. |
| LangChain | Criacao do agente analitico sobre o DataFrame. |
| Google Gemini | Modelo de IA usado pelo agente via `langchain-google-genai`. |
| python-dotenv | Carregamento das variaveis de ambiente do arquivo `.env`. |

## Arquitetura do Projeto

O projeto segue um fluxo em camadas:

1. **Extracao**: baixa dados brutos da CVM, Selic e IFIX.
2. **Processamento**: filtra ofertas de FIIs e padroniza colunas relevantes.
3. **Enriquecimento**: cruza ofertas com Selic e IFIX pela data de requerimento.
4. **Analise**: disponibiliza a base no dashboard e no agente de IA.

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
|   |-- data/
|   |   |-- raw/
|   |   |   |-- oferta_resolucao_160_bruto.csv
|   |   |   |-- selic_bruto.csv
|   |   |   |-- ifix_bruto.csv
|   |   |-- processed/
|   |   |   |-- ofertas_fiis_pronto_para_ia.csv
|   |-- data_extraction/
|   |   |-- cvm_extractor.py
|   |   |-- macro_extractor.py
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
| `src/data_extraction/macro_extractor.py` | Baixa Selic pelo Banco Central e IFIX via Yahoo Finance. |
| `src/data_processing/cleaner.py` | Filtra apenas ofertas de FIIs e seleciona as colunas relevantes. |
| `src/data_processing/enricher.py` | Cruza ofertas com Selic e IFIX e gera a base final processada. |
| `src/ai_core/agent.py` | Inicializa o agente LangChain/Gemini sobre a base final. |
| `src/frontend/app.py` | Dashboard Streamlit com filtros, rankings, comparacao de ofertas, base CVM e copiloto de IA. |
| `src/data/raw/` | Dados brutos baixados das fontes externas. |
| `src/data/processed/` | Dados prontos para analise e IA. |
| `venv/` | Ambiente virtual local. Nao faz parte do codigo-fonte. |

## Dados Gerados

| Arquivo | Descricao |
| --- | --- |
| `src/data/raw/oferta_resolucao_160_bruto.csv` | Base bruta de ofertas baixada da CVM. |
| `src/data/raw/selic_bruto.csv` | Serie diaria da Selic obtida no Banco Central. |
| `src/data/raw/ifix_bruto.csv` | Historico do IFIX obtido via `yfinance`. |
| `src/data/processed/ofertas_fiis_pronto_para_ia.csv` | Base final com ofertas de FIIs enriquecidas com Selic e IFIX. |

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

## Funcionalidades do Dashboard

- Filtros por periodo, coordenador lider, status e publico-alvo.
- Indicadores de volume total, quantidade de ofertas, ticket medio, Selic media e IFIX medio.
- Evolucao mensal de volume registrado.
- Distribuicao de volume por status e publico-alvo.
- Comparacao direta entre ofertas selecionadas.
- Ranking de coordenadores lideres por volume, quantidade, ticket medio e market share.
- Tabela da base processada com opcao de download do recorte filtrado.
- Copiloto de IA para perguntas em linguagem natural sobre a base.

## Limpeza Realizada

Foram removidos arquivos gerados e modulos que nao faziam parte do fluxo atual:

- `__pycache__/`: caches automaticos do Python.
- `src/data_extraction/bcb_extractor.py`: extrator legado que gerava arquivos em caminhos fora do padrao atual.
- `src/data_processing/data_processor.py`: processador legado que usava nomes de arquivos antigos e dados simulados para spread.

## Observacoes

- O dashboard nao usa dados mockados: ele le `src/data/processed/ofertas_fiis_pronto_para_ia.csv`.
- Se a base processada nao existir, rode `python src/main.py`.
- O arquivo `.env`, o `venv/` e os caches Python ficam fora do versionamento pelo `.gitignore`.
