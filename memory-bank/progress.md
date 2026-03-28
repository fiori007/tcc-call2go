# Progress — TCC Call2Go

## Histórico de Marcos

### ✅ Concluído (Fase 1 — Pipeline Original)
- **Coleta Spotify** — Script funcional, dados coletados em 12/03/2026 para 6 artistas
- **Coleta YouTube** — Script funcional com resolução dinâmica de canal, ~50 vídeos/artista
- **Detector Call2Go** — Motor regex implementado, classifica em `link_direto`, `texto_implicito`, `nenhum`
- **Data Warehouse** — SQLite com schema estrela
- **Análises estatísticas** — EDA, Mann-Whitney U, scatter cross-platform
- **Memory Bank** — Estrutura de contexto persistente

### ✅ Concluído (Fase 2 — Correções Metodológicas, 28/03/2026)
- **`artist_source_builder.py`** — Fonte oficial de artistas via playlists Spotify (reprodutível)
- **`sample_generator.py`** — Gerador de amostra aleatória para anotação manual (com seed fixo)
- **`cross_validator.py`** — Valida humano vs. máquina com métricas (Acurácia, Precisão, Recall, F1)
- **`agreement_report.py`** — Gera matriz de confusão e gráficos de concordância
- **`cross_platform_validator.py`** — A VERDADEIRA "volta": análise bidirecional YouTube ↔ Spotify
  - Direção A: YouTube → Spotify (Call2Go rate ↔ popularidade/seguidores)
  - Direção B: Spotify → YouTube (popularidade/seguidores ↔ views/engagement)
  - Síntese: classifica relação como Bidirecional / Unidirecional / Independente
  - Gera: heatmap de correlação, scatter plots por direção, relatório textual
- **Reorientação do foco** — De "impacto musical" para "confiabilidade metodológica + análise bidirecional"

### 🔲 Pendente (Ações Imediatas — Em Ordem)
1. Rodar `artist_source_builder.py` com playlists oficiais
2. Re-coletar YouTube/Spotify com nova base
3. Re-rodar `call2go_detector.py`
4. Gerar amostra de validação (`sample_generator.py`)
5. **ANOTAR MANUALMENTE** o ground truth (o aluno, não IA)
6. Rodar `cross_validator.py` — gerar métricas de confiabilidade (humano vs. máquina)
7. Rodar `agreement_report.py` — gerar visualizações de concordância
8. Rodar `cross_platform_validator.py` — análise bidirecional YouTube ↔ Spotify
9. Re-rodar análises estatísticas com dados validados
10. Escrever capítulo de Metodologia do TCC documentando todo o fluxo

### 🔲 Pendente (Melhorias Futuras)
- Coleta longitudinal do Spotify (múltiplas datas)
- Teste de correlação Spearman (views × popularity)  
- Análise de engagement rate (likes/views, comments/views)
- Expansão do detector para outras plataformas (Deezer, Apple Music)

## Observações Importantes
- **ALERTA:** Os dados atuais (6 artistas) foram selecionados sem critério oficial — devem ser refeitos
- **ALERTA:** Resultados das análises estatísticas atuais NÃO foram validados — não usar no TCC ainda
- A categoria `link_direto` tem amostra muito pequena (n≈1)
- Apenas 1 snapshot do Spotify (12/03/2026)
