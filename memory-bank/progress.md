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

### ✅ Concluído (Fase 3 — Automação da Validação, 29/03/2026)
- **`ground_truth_helper.py`** — NOVO: pré-preenche ground truth automaticamente (semi-automático)
  - Cruza amostra com dados brutos completos (descrição + channel_description)
  - Aplica detector regex + busca evidências textuais
  - Classifica confiança: ALTA / MEDIA / BAIXA
  - Dos 50 vídeos: 45 alta confiança, 5 para revisão humana
  - Distribuição: 5 link_direto, 5 texto_implicito, 40 nenhum
- **`sample_generator.py`** atualizado — agora inclui `channel_description_preview` e `manual_channel_call2go_type`
- **`cross_validator.py`** atualizado — validação em 3 níveis:
  - Nível 1: Só vídeo (humano vs. regex no vídeo)
  - Nível 2: Combinado (humano vs. regex vídeo+canal)
  - Nível 3: Canal isolado (humano vs. regex no perfil do canal)
- **`agreement_report.py`** atualizado — 2 matrizes de confusão (combinado + só vídeo), imagens ≤1800px
- **`call2go_detector.py`** corrigido — adicionado `sptfy.com` no regex (domínio oficial Spotify encontrado nos dados da Anitta)
- **Bug fix:** Links `http://sptfy.com/...` estavam sendo classificados como `texto_implicito` em vez de `link_direto`

### 🔲 Pendente (Ações Imediatas — Em Ordem)
1. 🔴 **ALUNO:** Revisar `data/validation/ground_truth_prefilled.csv` (5 vídeos de média confiança)
2. 🔴 **ALUNO:** Salvar como `data/validation/ground_truth.csv`
3. Rodar `cross_validator.py` — gerar métricas de confiabilidade (humano vs. máquina)
4. Rodar `agreement_report.py` — gerar visualizações de concordância
5. Rodar `cross_platform_validator.py` — análise bidirecional YouTube ↔ Spotify
6. Re-rodar análises estatísticas com dados validados
7. Escrever capítulo de Metodologia do TCC documentando todo o fluxo

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
