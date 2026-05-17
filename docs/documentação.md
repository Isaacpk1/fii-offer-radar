# Agente Inteligente de Análise e Contextualização de Ofertas Primárias
**Parceiro:** Banco BTG Pactual  
**Entrega Final:** 28 de maio de 2026

---

## Sumário

1. [Objetivo do Projeto](#objetivo-do-projeto)
2. [Estrutura de Pastas](#estrutura-de-pastas)
3. [Estrutura do Banco de Dados](#estrutura-do-banco-de-dados)
4. [Tecnologias Utilizadas](#tecnologias-utilizadas)
5. [Fontes de Estudo](#fontes-de-estudo)

---

## Objetivo do Projeto

O projeto propõe o desenvolvimento de um **agente inteligente** capaz de coletar automaticamente dados de ofertas primárias de renda fixa (CDB, LCI, LCA) de múltiplas instituições financeiras (BTG Pactual, XP, etc.), analisá-los de forma estruturada e contextualizar suas variações à luz de fatores macroeconômicos e informacionais.

### O sistema visa:

- Automatizar a coleta de dados de ofertas primárias em diferentes plataformas via APIs públicas ou web scraping
- Estruturar e padronizar informações para análise comparativa entre instituições
- Identificar diferenças relevantes entre taxas de ativos similares (ex: CDB 110% CDI vs CDB 105% CDI)
- Correlacionar variações nas taxas com fatores macroeconômicos (Selic, IPCA, CDI) e eventos recentes (decisões do Copom, inflação, cenário fiscal)
- Gerar relatórios analíticos que combinem análise quantitativa e interpretação contextual via LLM
- Disponibilizar os insights em uma interface interativa (dashboard Streamlit)

---

## Estrutura de Pastas

```
projeto_scraper/
│
├── main.py                    # Ponto de entrada da aplicação; orquestra o agente
│
├── src/                       # Código-fonte principal
│   ├── ai_core/               # Núcleo de inteligência artificial
│   │   └── ...                # Agente LangChain, prompts, chains, memória vetorial
│   │
│   ├── data_extraction/       # Coleta de dados
│   │   └── ...                # Scrapers (Playwright), clientes de API, python-bcb
│   │
│   ├── data_processing/       # Tratamento e padronização
│   │   └── ...                # Normalização de taxas, parsing, limpeza de dados
│   │
│   └── frontend/              # Interface do usuário
│       └── ...                # Dashboard Streamlit com gráficos Plotly
│
├── docs/                      # Documentação do projeto
│   └── ...                    # Diagramas, modelagem de dados, decisões técnicas
│
├── tests/                     # Testes automatizados
│   └── ...                    # Testes unitários e de integração
│
├── venv/                      # Ambiente virtual Python (não versionar)
├── .env                       # Variáveis de ambiente (chaves de API, credenciais)
└── .gitignore                 # Arquivos ignorados pelo Git
```

> **Nota:** O arquivo `.env` nunca deve ser versionado. Ele contém credenciais sensíveis como chaves de API (OpenAI, etc.). Utilize `.env.example` como template público.

---

## Estrutura do Banco de Dados

O projeto utiliza uma arquitetura **híbrida** com dois domínios de persistência:

- **Banco Relacional (PostgreSQL/SQLite):** dados estruturados de ofertas, instituições, indexadores e indicadores macroeconômicos.
- **Banco Vetorial (ex: Pinecone, pgvector, FAISS):** textos não-estruturados de notícias e análises geradas pela IA, armazenados como embeddings para busca semântica.

---

### Diagrama de Entidade-Relacionamento

```
@startuml
' Configurações Visuais
skinparam linetype ortho
skinparam nodesep 100
skinparam ranksep 80
hide circle

' Definição de Cores para distinção de domínios
!define RELATIONAL_COLOR #E1F5FE
!define VECTOR_COLOR #F3E5F5
!define ORCHESTRATION_COLOR #FFF9C4

header Agente Inteligente BTG - Modelagem de Dados Documentada
footer Engenharia de Software - Padrão RAG + SQL

' --- DOMÍNIO DE ORQUESTRAÇÃO ---
package "Orquestração e Rastreabilidade" {
  entity "execucoes_agente" as exec << (T, ORCHESTRATION_COLOR) >> {
    * id_execucao : UUID <<PK>> ' Identificador único de cada rodada do agente
    --
    data_inicio : TIMESTAMP ' Momento exato em que o script iniciou
    data_fim : TIMESTAMP ' Momento em que a execução finalizou
    status : VARCHAR(20) ' Ex: "Sucesso", "Falha", "Em Andamento"
    log_erro : TEXT ' Registro detalhado de erro caso o scraper ou a IA falhem
  }
}

' --- DOMÍNIO RELACIONAL (SQL) ---
package "Banco de Dados SQL (Estruturado)" {
  
  entity "instituicoes" as inst << (T, RELATIONAL_COLOR) >> {
    * id_instituicao : INT <<PK>> ' Chave primária da instituição
    --
    nome_fantasia : VARCHAR(100) ' Nome comercial (Ex: BTG Pactual, XP, Itaú)
    tipo : VARCHAR(50) ' Classificação (Ex: Banco Múltiplo, Corretora)
  }

  entity "indexadores" as idx << (T, RELATIONAL_COLOR) >> {
    * id_indexador : INT <<PK>> ' Chave primária do indexador
    --
    sigla : VARCHAR(10) ' Código da taxa de referência (Ex: CDI, IPCA, PRE)
  }

  entity "ofertas_primarias" as ofertas << (T, RELATIONAL_COLOR) >> {
    * id_oferta : UUID <<PK>> ' Identificador único da oferta coletada
    --
    id_instituicao : INT <<FK>> ' Qual banco/corretora está emitindo
    id_indexador : INT <<FK>> ' A qual taxa o ativo está atrelado
    id_execucao : UUID <<FK>> ' Em qual rodada do robô esse dado foi coletado
    tipo_ativo : VARCHAR(50) ' Categoria do produto (Ex: CDB, LCI, LCA)
    taxa_numerica : DECIMAL(10,4) ' Percentual oferecido, armazenado com alta precisão
    data_vencimento : DATE ' Prazo final em que o investidor resgata o dinheiro
    data_coleta : TIMESTAMP ' Momento exato da raspagem no site/API
  }

  entity "indicadores_macro" as macro << (T, RELATIONAL_COLOR) >> {
    * id_indicador : INT <<PK>> ' Identificador único do registro macroeconômico
    --
    id_indexador : INT <<FK>> ' Link com o tipo de taxa (Ex: CDI)
    data_referencia : DATE ' Data à qual a taxa macro se aplica (Ex: Selic de hoje)
    valor_percentual : DECIMAL(10,4) ' Valor oficial da taxa no mercado para base de comparação
  }

  entity "ofertas_destaque_analise" as destaque << (T, RELATIONAL_COLOR) >> {
    * id_analise : UUID <<FK>> ' ID da análise feita pelo LangChain
    * id_oferta : UUID <<FK>> ' ID da oferta específica que a IA analisou
    --
    motivo_destaque : VARCHAR(255) ' Breve texto da IA justificando por que escolheu essa oferta
  }
}

' --- DOMÍNIO VETORIAL (VEC) ---
package "Banco Vetorial (Não-Estruturado)" {
  
  entity "eventos_noticias" as noticias << (V, VECTOR_COLOR) >> {
    * id_evento : INT <<PK>> ' Identificador do evento/notícia
    --
    data_publicacao : DATE ' Data de publicação do relatório ou notícia
    manchete : TEXT ' Título principal do texto raspado
    conteudo_bruto : TEXT ' Corpo completo do texto lido da fonte
    vetor_embedding : VECTOR(1536) ' Representação matemática do texto para busca semântica da IA
  }

  entity "analises_ia_contexto" as analise << (V, VECTOR_COLOR) >> {
    * id_analise : UUID <<PK>> ' Identificador do relatório gerado pela IA
    --
    id_execucao : UUID <<FK>> ' Referência à rodada do agente que gerou o texto
    data_analise : TIMESTAMP ' Momento em que a análise foi concluída
    insight_gerado : TEXT ' Texto narrativo consolidando as conclusões da IA
    impacto_macro : TEXT ' Avaliação da IA sobre como os eventos macro impactaram as taxas
    vetor_resumo : VECTOR(1536) ' Vetor matemático da análise, usado para "memória" do agente
  }
}

' --- RELACIONAMENTOS ---

' Orquestração ligando a tudo
exec ||--o{ ofertas
exec ||--o{ analise

' Relacional Puro
inst ||--o{ ofertas
idx ||--o{ ofertas
idx ||--o{ macro

' Conexão Híbrida (SQL <-> IA)
analise ||--o{ destaque
ofertas ||--o{ destaque

@enduml
```

---

### Script SQL de Criação

```sql
-- ==============================================================================
-- 1. DOMÍNIO DE ORQUESTRAÇÃO
-- ==============================================================================

CREATE TABLE execucoes_agente (
    id_execucao UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_inicio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_fim TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- Ex: 'Em Andamento', 'Sucesso', 'Falha'
    log_erro TEXT
);

-- ==============================================================================
-- 2. DOMÍNIO DE CATÁLOGOS (DIMENSÕES)
-- ==============================================================================

CREATE TABLE instituicoes (
    id_instituicao SERIAL PRIMARY KEY, -- SERIAL gera um auto-incremento (1, 2, 3...)
    nome_fantasia VARCHAR(100) NOT NULL,
    tipo VARCHAR(50) NOT NULL -- Ex: 'Banco Múltiplo', 'Corretora'
);

CREATE TABLE indexadores (
    id_indexador SERIAL PRIMARY KEY,
    sigla VARCHAR(10) NOT NULL UNIQUE -- UNIQUE impede que "CDI" seja cadastrado duas vezes
);

-- ==============================================================================
-- 3. DOMÍNIO DE CAPTAÇÃO (FATO PRINCIPAL)
-- ==============================================================================

CREATE TABLE ofertas_primarias (
    id_oferta UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_instituicao INT NOT NULL,
    id_indexador INT NOT NULL,
    id_execucao UUID NOT NULL,
    tipo_ativo VARCHAR(50) NOT NULL, -- Ex: 'CDB', 'LCI', 'LCA'
    taxa_numerica DECIMAL(10,4) NOT NULL, -- Precisão financeira garantida
    data_vencimento DATE NOT NULL,
    data_coleta TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Definição das Chaves Estrangeiras (Constraints de Integridade)
    CONSTRAINT fk_oferta_instituicao 
        FOREIGN KEY (id_instituicao) REFERENCES instituicoes (id_instituicao),
    CONSTRAINT fk_oferta_indexador 
        FOREIGN KEY (id_indexador) REFERENCES indexadores (id_indexador),
    CONSTRAINT fk_oferta_execucao 
        FOREIGN KEY (id_execucao) REFERENCES execucoes_agente (id_execucao)
);

-- ==============================================================================
-- 4. DOMÍNIO DE CONTEXTO ESTRUTURADO
-- ==============================================================================

CREATE TABLE indicadores_macro (
    id_indicador SERIAL PRIMARY KEY,
    id_indexador INT NOT NULL,
    data_referencia DATE NOT NULL,
    valor_percentual DECIMAL(10,4) NOT NULL,
    
    CONSTRAINT fk_macro_indexador 
        FOREIGN KEY (id_indexador) REFERENCES indexadores (id_indexador)
);

-- ==============================================================================
-- 5. TABELA ASSOCIATIVA (PONTE COM O VETORIAL)
-- ==============================================================================

CREATE TABLE ofertas_destaque_analise (
    -- id_analise aponta para a tabela 'analises_ia_contexto'. Se essa tabela 
    -- estiver num banco NoSQL/Vetorial (como Pinecone), não usamos CONSTRAINT FOREIGN KEY aqui, 
    -- deixamos apenas como uma referência lógica do tipo UUID.
    id_analise UUID NOT NULL, 
    id_oferta UUID NOT NULL,
    motivo_destaque VARCHAR(255) NOT NULL,
    
    -- A chave primária é composta pelos dois IDs para evitar duplicação
    PRIMARY KEY (id_analise, id_oferta),
    
    CONSTRAINT fk_destaque_oferta 
        FOREIGN KEY (id_oferta) REFERENCES ofertas_primarias (id_oferta)
);

INSERT INTO indexadores (sigla) 
VALUES ('Selic'), ('IPCA'), ('CDI');

ALTER TABLE indicadores_macro 
ADD CONSTRAINT unique_indexador_data UNIQUE (id_indexador, data_referencia);
```

---

## Tecnologias Utilizadas

### Linguagem Principal

| Tecnologia | Uso |
|---|---|
| **Python 3.13** | Linguagem base de todo o projeto |

### Ferramentas Principais

| Tecnologia | Camada | Finalidade |
|---|---|---|
| **LangChain** | IA / Orquestração | Constrói o loop de raciocínio do agente, conecta o LLM às ferramentas de coleta/análise e gerencia a memória vetorial. Define *chains*, *agents* e *tools* de forma declarativa. |
| **Streamlit** | Frontend / Interface | Dashboard interativo com filtros por instituição, tipo de ativo, indexador e período. Atualização dinâmica e integração nativa com Python. |

### Ferramentas Complementares

| Tecnologia | Camada | Finalidade |
|---|---|---|
| **Playwright** | Coleta de Dados | Automação de browser para scraping em plataformas sem API pública. Gera código automaticamente via Codegen. |
| **Plotly** | Visualização | Gráficos interativos dentro do Streamlit: séries temporais de taxas, comparativos por instituição e tipo de ativo. |
| **python-bcb** | Dados Macroeconômicos | Coleta de indicadores oficiais do Banco Central (Selic, IPCA, CDI) diretamente no formato DataFrame pandas via SGS. |
| **st-aggrid** | Frontend | Tabelas interativas avançadas no Streamlit com filtros, ordenação e seleção de linhas, integradas ao Plotly. |

### Stack de IA

| Componente | Tecnologia Sugerida |
|---|---|
| Modelo de linguagem (LLM) | OpenAI GPT-4o / Claude via API |
| Embeddings | `text-embedding-3-small` (OpenAI) — 1536 dimensões |
| Banco vetorial | Pinecone, pgvector (PostgreSQL) ou FAISS (local) |

---

## Fontes de Estudo

### LangChain

| Recurso | Link |
|---|---|
| Visão Geral | [docs.langchain.com](https://docs.langchain.com/oss/python/langchain/overview) |
| Quickstart | Primeira aplicação funcional passo a passo |
| Agents | Como criar agentes autônomos com encadeamento de ações |
| Tools | Integração com funções externas (scraping, APIs, DBs) |

### Streamlit

| Recurso | Link |
|---|---|
| Documentação Principal | [docs.streamlit.io](https://docs.streamlit.io) |
| Session State | Gerenciamento de estado entre interações (essencial para filtros dinâmicos) |
| Cache Data | Otimização para evitar reprocessamento a cada interação |

### Playwright

| Recurso | Descrição |
|---|---|
| Introdução | Setup e primeiros scripts de automação |
| Locators | Seleção de elementos da página |
| Codegen | Geração automática de código a partir de navegação gravada |

### python-bcb

| Recurso | Descrição |
|---|---|
| Documentação oficial | Todos os módulos disponíveis |
| SGS — Séries Temporais | Como buscar IPCA, Selic e CDI em DataFrame pandas |
| Catálogo SGS (BCB) | Código numérico de qualquer indicador disponível |

### Plotly

| Recurso | Descrição |
|---|---|
| Plotly Express | API simplificada para criação rápida de visualizações |
| Time Series | Gráficos de séries temporais (evolução de taxas) |

---

## Datas Importantes

| Evento | Data |
|---|---|
| Primeiro encontro com o parceiro (BTG) | 08 de maio de 2026 |
| **Entrega final** | **28 de maio de 2026** |

---

*Documentação gerada em 17/05/2026*