# Project Guidelines — TCC Call2Go

## Memory Bank
Antes de responder qualquer pergunta sobre este projeto, leia os arquivos do memory bank em `memory-bank/` para entender o contexto completo:

- `memory-bank/projectbrief.md` — Visão geral, hipóteses e escopo
- `memory-bank/productContext.md` — Problema de pesquisa e contexto
- `memory-bank/activeContext.md` — Foco atual e decisões recentes
- `memory-bank/systemPatterns.md` — Arquitetura, pipeline ETL, schema DB e padrões regex
- `memory-bank/techContext.md` — Stack, APIs, dependências e limitações
- `memory-bank/progress.md` — O que foi feito e próximos passos

## Convenções
- Código em Python 3, nomes de variáveis/funções em inglês, comentários em português
- Scripts standalone com `if __name__ == "__main__"`
- Dados de referência em `data/seed/`, brutos em `data/raw/`, processados em `data/processed/`, gráficos em `data/plots/`
- Coletores em `src/collectors/`, processamento em `src/processors/`, análises em `src/analytics/`, banco em `src/db/`
- Autenticação via `.env` (nunca commitar chaves)
- Gráficos acadêmicos com DPI 300

## Contexto Acadêmico
Este é um TCC (Trabalho de Conclusão de Curso). Priorize rigor estatístico, reprodutibilidade e clareza nas explicações.
