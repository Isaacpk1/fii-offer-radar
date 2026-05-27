# Escopo Do Produto

Este projeto e uma ferramenta de triagem e analise de ofertas primarias de FIIs. Ele organiza dados para acelerar a leitura do analista, mas nao substitui decisao de investimento, diligencia juridica ou fonte institucional de mercado.

## Pergunta Central

```text
Esta oferta primaria merece prioridade de analise considerando preco de emissao,
valor patrimonial, mercado secundario quando houver, liquidez, historico,
macro e qualidade dos dados?
```

## Fora Do Escopo Atual

- Screener completo de FIIs.
- Recomendacao automatica de compra/venda.
- Preco B3 institucional em tempo real.
- Monitor de novas ofertas em background continuo.
- Cobertura garantida para todos os fundos.
- Analise juridica dos documentos.

## Funcionalidades Atuais

| Area | Status | Observacao |
| --- | --- | --- |
| Coleta CVM 160 | Implementado | Fonte oficial para ofertas. |
| Macro BCB | Implementado | Selic, CDI, IPCA 12m e USD/BRL. |
| IFIX | Parcial | Depende da cobertura retornada pela fonte de mercado. |
| Informe mensal FII | Implementado com cobertura variavel | VP/C, PL, cotistas e campos operacionais conforme dados CVM. |
| Mapeamento ticker | Implementado com cache | Usa CNPJ -> ticker quando a fonte permite mapear. |
| Mercado B3/yfinance | Parcial | Apenas para tickers mapeados/coletados. |
| Documentos de oferta | Implementado | Manifesto, download e extracao deterministica/IA. |
| DY projetado | Parcial | Depende dos documentos; dado prospectivo do emissor. |
| Confianca auditavel | Implementado | Score de dados, sinais e contexto. |
| Noticias | Parcial | Contexto qualitativo best effort. |
| Agente IA | Implementado | Copiloto com tools e output estruturado em rankings. |
| Runner autonomo | Manual/agendavel | Existe script, nao roda como servico continuo. |
| Status monitor | Batch | Roda no pipeline e grava estado/alertas. |

## Abas Do Dashboard

| Aba | Finalidade |
| --- | --- |
| Tese da Oferta | Ranking, ficha de decisao, confianca e sinais por processo CVM. |
| Mercado | Volumes, status, coordenadores e contexto macro das ofertas. |
| Ofertas | Comparacao de processos e filtros operacionais. |
| Suporte FII | Dados do fundo por tras da oferta, incluindo casos sem B3. |
| Qualidade | Cobertura de dados e lacunas por tabela/coluna. |
| Tabelas | Exploracao direta do warehouse. |
| Copiloto | Perguntas em linguagem natural e acoes do agente. |

## Como Interpretar Suporte FII

A aba Suporte FII nao mostra apenas fundos com ticker. Ela tambem lista fundos sem coleta B3 quando existe informacao util no warehouse.

- `preco_cota`, `p_vp` e `volume_medio_diario`: dependem de ticker mapeado e coleta de mercado.
- `valor_cota_vpc`, `patrimonio_liquido`, `numero_cotistas` e dados de informe: podem existir mesmo sem B3.
- `total_emissoes` e `volume_total_ofertas`: vem do historico CVM.

Ausencia de B3 significa ausencia de comparavel de mercado coletado, nao ausencia total de dados.

## Interpretacao De DY

- `dy_12m_historico_sobre_emissao`: rendimento historico estimado sobre o preco de emissao.
- `dy_projetado_oferta`: dado prospectivo extraido de documento de oferta quando encontrado.

O DY projetado deve ser tratado como guidance/documento do emissor, nao como dado auditado.

## Alertas E Automacao

O projeto tem duas pecas de automacao:

- `status_monitor.py`: compara status atual com snapshot anterior durante o pipeline.
- `autonomous_runner.py`: executa tarefas do agente e grava alertas quando chamado manualmente ou por agendamento externo.

Nenhuma das duas roda continuamente sem agendamento. Para execucao diaria, use Task Scheduler/cron chamando:

```powershell
.\venv\Scripts\python.exe src/main.py --force
.\venv\Scripts\python.exe src/ai_core/autonomous_runner.py
```

## Criterio De Uso

Use o sistema para:

- priorizar ofertas;
- identificar lacunas de dados;
- comparar emissao vs VP/C e B3 quando houver;
- gerar brief preliminar;
- registrar decisoes internas;
- orientar proxima diligencia.

Nao use o sistema isoladamente para:

- aprovar investimento;
- substituir validacao juridica;
- assumir liquidez/preco onde nao ha ticker mapeado;
- tratar DY projetado como fato realizado.
