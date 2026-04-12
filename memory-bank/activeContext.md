# Active Context — TCC Call2Go

## Foco Atual (Fase 9 — Re-execução + Censo Completo, 11/04/2026)
Pipeline re-executado do zero com dados frescos das APIs. XLSX censo gerado com 920 vídeos para anotação humana completa.

**Próximo passo:** 🔴 Aluno anota TODOS os 920 vídeos no XLSX censo (SIM/NÃO), salva como ground_truth.csv, e roda cross_validator.

## Estado do Projeto (11/04/2026)

### Coleta de Dados ✅ (Re-executada 11/04/2026)
- **Artistas:** 50 artistas brasileiros via playlists dinâmicas do Spotify
  - Playlists hardcoded (Top 50 Brasil, Viral 50, Top Hits) retornaram 404
  - Fallback dinâmico encontrou 5 playlists alternativas → 340 candidatos → Top 50 por views
- **Vídeos YouTube:** 920 vídeos (20 mais visualizados por artista), 46 artistas com vídeos
- **Spotify:** Métricas coletadas para 50 artistas (2026-04-11)
- **Canal scraping:** 51 canais processados com links da aba Sobre

### Detector Call2Go ✅
- 100% regex (re.search), sem IA/ML
- 77 testes unitários — todos passam

### Análises Estatísticas ✅ (Re-executadas 11/04/2026)
- Pipeline 11 etapas concluído em 5.6 min
- Boxplot, scatter, heatmap bidirecional, relatórios gerados

### Validação — EM ANDAMENTO
- **Fase 8:** Amostra adversarial (91 videos) — Kappa canal 0.80, vídeo 0.45, combinado 0.09
- **Fase 9:** XLSX censo com 920 vídeos gerado para anotação humana completa (SIM/NÃO)
  - `data/validation/blind_annotation_census.xlsx` — 920 linhas, dropdowns SIM/NÃO
  - Após anotação: cross_validator.py já aceita formato SIM/NÃO via `_map_to_binary()`

### Testes ✅
- 77 testes em `tests/test_call2go_detector.py` — todos passam

### Pipeline ✅
- Roda sem erros em Windows cp1252 (encoding fix aplicado)
- 11 etapas, 5.9s (skip-collect)
- requirements.txt totalmente pinado + scikit-learn + pytest

## Próximas Ações (Prioridade)
1. 🔴 **ALUNO:** Alinhar com orientador sobre Direção B (correlação vs. links reais Spotify→YouTube)
2. [ ] Escrever capítulo de Metodologia documentando validação circular + correção + resultados reais
3. [ ] Escrever capítulo de Resultados com Kappa 3 níveis + IC 95% + matrizes de confusão
4. [ ] Analisar os 16 FPs do nível Vídeo — entender por que o detector marca mas o humano não
5. [ ] Analisar os 9 FNs do nível Canal — links Spotify não scrapeados (lnk.to, etc.)
