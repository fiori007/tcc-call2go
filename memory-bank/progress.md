# Progress — TCC Call2Go

## Estado Atual (18/04/2026)
- **Fase 10 concluída:** Pipeline completo executado com sucesso (67 artistas, 1.641 vídeos)
- **Detecção de Labels:** 71 → 67 artistas (4 labels removidos automaticamente)
- **Fallback regex na bio:** +30 canais detectados, +18 combinados (Spotify + bit.ly capturado)
- **Resultados:** Mann-Whitney p=0.151, NÃO rejeita H0. Relação UNIDIRECIONAL Spotify→YouTube.
- **Próximo passo:** 🔴 Anotar 1.641 vídeos no Census Excel para validação manual

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

### ✅ Concluído (Fase 4 — Qualidade dos Dados, 29/03/2026)
- **`channel_link_scraper.py`** — NOVO: web scraper 2-fases (página principal + /about) para links estruturados
  - Fix crítico: decode `\u0026` no JSON do YouTube → URLs completas extraídas
  - **Descoberta de canal oficial para OAC**: busca automática via YouTube Search
    - 9/9 canais oficiais encontrados para artistas com OAC
  - Resultado: **12/20 artistas** têm Spotify na aba Sobre (antes: 2/20 → 7/20 → 12/20)
  - Detecta canais OAC (auto-gerados): 9/20 canais são OAC
  - Cache em `data/raw/channel_links_scraped.json` (29 canais: 20 primários + 9 oficiais)
- **`call2go_detector.py`** — melhorias significativas:
  - `is_auto_generated()` — detecta vídeos "Provided to YouTube by..." (450/1000 = 45%)
  - `detect_call2go_channel_scraped()` — detecta Call2Go via links scrapeados (mais confiável)
  - Removido `\bspotify\b` genérico de `detect_call2go_channel()` (causava falsos positivos)
  - Adicionado filtro de menções narrativas ("charts do Spotify" ≠ Call2Go)
  - Novas colunas: `is_auto_generated`, `is_oac_channel`
  - Resultado: 0 `texto_implicito` (todos agora são `link_direto` ou `nenhum`)
- **`ground_truth_helper.py`** atualizado:
  - Integra links scrapeados como evidência principal
  - Flags auto-gen e OAC para contexto
  - **50/50 alta confiança** (antes: 45/50) — melhoria de 100%
  - Distribuição: 31 link_direto, 0 texto_implicito, 19 nenhum
- **Correção Grupo Menos É Mais** — "200 dias nos charts do Spotify" não é mais falso positivo

### ✅ Concluído (Fase 5 — Novo Pipeline Top 50 BR, 30-31/03/2026)
- Pipeline completo reconstruído: 50 artistas Top BR, 1000 vídeos, 11 etapas
- `artist_source_builder.py` reescrito (Spotify playlists → YouTube viewCount → dedup)
- `youtube_collector.py` otimizado (89% menos quota com `playlistItems.list`)
- `call2go_detector.py` — Nível 2 (texto da bio) removido, apenas links
- Coleta concluída em 31/03 após reset de quota

### ✅ Concluído (Fase 6 — Correções de Precisão, 31/03/2026)

#### Problemas Encontrados na Revisão Humana do Ground Truth
- **Anitta (oyhlZhUjaeQ):** `Spotify | https://Anitta.lnk.to/Spotify` NÃO detectado — `lnk.to` redirect fora do regex
- **NATTAN (c7Fv2roodqI):** Falso positivo — `stream.*spotify` greedy casou 207 chars de bio narrativa
- **MJ Records:** Label brasileira mapeada para canal do Michael Jackson (UCID errado). 20 vídeos contaminados
- **Channel ID mismatch:** 4 artistas (Anitta, Panda, Turma do Pagode, Léo Santana) com channel_id diferente no seed vs JSONL
- **28 links redirect perdidos:** Mc Livinho (`bit.ly/LivinhoNoSpotify`), Anitta (`lnk.to`), Pablo (`smarturl.it`)

#### Correções Aplicadas
1. **call2go_detector.py** — 6 fixes:
   - 3 novas camadas de link: domínio direto + labeled redirect + URL com spotify/sptfy no path
   - Greedy fix: `stream.*spotify` → `.{0,50}` (range limitado)
   - Padrões implícitos: `ou[çc]a\b.{0,50}\bspotify` (aceita palavras no meio)
   - Nova fonte `ambos` (vídeo + canal com Call2Go)
   - Seed channel fallback para mismatches
2. **ground_truth_helper.py** — Padrões de evidência atualizados (redirect + range limitado)
3. **hypothesis_testing.py** — Grupos corrigidos: `Com Call2Go` vs `Sem Call2Go` (era `texto_implicito` vs `nenhum` → NaN)
4. **spotify_impact_analysis.py** — Mesma correção de grupos
5. **MJ Records removido:** artistas.csv (50→49), JSONL (1000→980 vídeos)

#### Resultados Após Correções
- **Detecção:** 575 link_direto (58.7%), 0 texto_implicito (0%), 405 nenhum (41.3%)
- **Fontes:** 494 canal, 66 ambos, 15 vídeo, 405 nenhum
- **Mann-Whitney:** U=118004, p=0.35983 — **NÃO REJEITA H0**
- **Cross-platform:** U=169415.5, p=0.99819 — **NÃO REJEITA H0**
- **Bidirecional:** UNIDIRECIONAL Spotify → YouTube (ρ=0.392***, Call2Go Rate ρ=-0.086 ns)
- **Ground truth:** 49 alta confiança, 1 flagado (Eric Land — narrativa), vs 6 flagados antes
- **Verificações:** Anitta=link_direto+ambos ✅, NATTAN=nenhum ✅, Panda=20/20 detectados ✅

#### Coleta de Dados (30-31/03/2026)
- **Seed:** 49 artistas — `data/seed/artistas.csv` (MJ Records removido — canal incorreto)
  - Top 3: Marília Mendonça (20.6B views, 39.7M followers), Gusttavo Lima (18.5B), Henrique & Juliano (14.3B)
- **Spotify:** `data/raw/spotify_metrics_2026-03-30.csv` — 50 artistas coletados
- **Channel scraping:** `data/raw/channel_links_scraped.json` — 52 entradas (50 + 2 oficiais para OACs)
  - 29 com link Spotify no About, 2 OAC detectados
- **YouTube:** `data/raw/youtube_videos_raw.jsonl` — 980 vídeos (20/artista × 49), 0 erros

#### Detecção Call2Go (31/03/2026) — Antes das Correções da Fase 6
- **1.000 vídeos processados (dados originais antes de remover MJ Records):**
  - 528 link_direto (52.8%), 48 texto_implicito (4.8%), 424 nenhum (42.4%)
  - Fontes: 475 canal, 101 vídeo, 424 nenhum
  - 40 auto-gerados (4%), 960 orgânicos
- **Após Fase 6 (980 vídeos):** ver seção Fase 6 acima

#### Pipeline Steps 6-11 (31/03/2026) — Re-executados após correções da Fase 6
- **Step 6 — DB Build:** `call2go.db` (dim_artist, fact_yt_videos, fact_spotify_metrics)
- **Step 7 — EDA:** link_direto média 46.1M views vs nenhum 19.1M (N=1240 registros cruzados)
  - Boxplot: `data/plots/boxplot_call2go_views.png`
- **Step 8 — Hypothesis Testing:** Mann-Whitney U=118004, p=0.35983
  - **NÃO REJEITA H0:** Não há diferença significativa de views entre vídeos com/sem Call2Go
- **Step 9 — Cross-Platform:** Mann-Whitney U=169415.5, p=0.99819
  - **NÃO REJEITA H0:** Call2Go no YouTube não impacta popularidade no Spotify
  - Média Pop sem Call2Go: 74.77, com Call2Go: 73.58
  - Scatter: `data/plots/scatter_cross_platform.png`
- **Step 10 — Sample Generation:** 50 vídeos de 980 (seed=42)
  - Output: `data/validation/manual_sample.csv`
- **Step 11 — Bidirectional Validation:**
  - Direção A (YT→Spotify): Call2Go Rate ↔ Pop ρ=-0.086, p=0.556 — **NÃO significativo**
  - Direção B (Spotify→YT): Pop ↔ Avg Views ρ=0.392, p=0.0054*** — **SIGNIFICATIVO**
  - Direção B: Followers ↔ Avg Engagement ρ=0.380, p=0.0071***
  - Per-video: Pop ↔ Views ρ=0.344, p≈0 (N=980)
  - **Classificação: UNIDIRECIONAL Spotify → YouTube** (α=0.1)
  - Outputs: direction_a, direction_b, heatmap, cross_platform_report.txt, artist_cross_platform_profile.csv

### ✅ Concluído (Fase 8 — A Volta: Cross-Validation Real, 10/04/2026)

#### Anotação Humana Cega
- Aluno anotou 91 vídeos adversariais em Excel formatado
- Formato: SIM/NÃO binário (válido: texto_implicito=0 no dataset)
- Lógica combinado: AND (vídeo E canal) — diferente do detector que usa OR
- 100% confiança ALTA, 0 notas
- Distribuição: video=13 SIM/70 NÃO, canal=54 SIM/29 NÃO, combinado=12 SIM/71 NÃO

#### Adaptações de Código
- cross_validator.py reescrito: auto-detect sep (`;`), mapeamento binário (SIM/NÃO → com_call2go/sem_call2go), 3 níveis independentes
- agreement_report.py adaptado: labels binários, 3 matrizes de confusão (vídeo, canal, combinado)
- Novas funções: `_map_to_binary()`, `_detect_separator()`

#### RESULTADOS REAIS — Humano vs. Máquina (91 vídeos adversariais)
- **Nível 1 (Vídeo):** Acurácia 82.4% [74.7%, 90.1%], **Kappa 0.4493 [0.24, 0.64] — MODERADO**
  - 16 FPs: detector marca com_call2go mas humano diz sem_call2go
  - com_call2go: P=36% R=100% F1=53% | sem_call2go: P=100% R=80.5% F1=89%
- **Nível 2 (Canal):** Acurácia 90.1% [83.5%, 95.6%], **Kappa 0.8040 [0.68, 0.91] — SUBSTANCIAL**
  - 9 FNs: humano vê Spotify mas detector não pega (Anitta lnk.to, Panda sem scraping)
  - com_call2go: P=100% R=82.4% F1=90% | sem_call2go: P=81.6% R=100% F1=90%
- **Nível 3 (Combinado):** Acurácia 45.1% [35.2%, 54.9%], **Kappa 0.0947 [0.03, 0.17] — FRACO**
  - 50 discordâncias: ARTEFATO METODOLÓGICO (humano AND vs detector OR)
  - NÃO é falha do detector — diferença de definição de "combinado"

#### Interpretação
- Nível 1 (Vídeo): detector é CONSERVADOR — recall perfeito mas precisão baixa (FPs por regex broad)
- Nível 2 (Canal): detector é CONFIÁVEL — Kappa substancial, quase perfeito
- Nível 3 (Combinado): Kappa fraco é explicado pela diferença AND/OR, não por falha
- Resultado honesto: detector regex é confiável para canal (Kappa 0.80), moderado para vídeo (Kappa 0.45)

#### Artefatos Gerados
- `data/validation/cross_validation_report.csv` — 91 linhas, 3 níveis
- `data/validation/cross_validation_report_metrics.json` — Kappa + IC 95% para cada nível
- `data/plots/confusion_matrix_combined.png` — Humano AND vs Detector OR
- `data/plots/confusion_matrix_video_only.png` — Humano vs Detector (vídeo)
- `data/plots/confusion_matrix_channel_only.png` — Humano vs Detector (canal)
- `data/plots/validation_metrics_per_class.png` — P/R/F1 por classe
- 77 testes unitários continuam passando

### ✅ Concluído (Fase 10 — Nova Base Temporal + Pipeline Completo, 16-18/04/2026)

#### Etapa 1: Identificação de artistas por persistência cross-platform
- **`src/processors/chart_processor.py`** — NOVO: processador de charts completo
  - Processa 13 CSVs Spotify (Top 200 BR) + 13 CSVs YouTube (Top 100 BR), Q1 2026
  - Extrai artistas de cada track: Spotify split por `,`, YouTube split por ` & `
  - **Duo-aware split** para YouTube: identifica 38 duplas/grupos do Spotify
    (29 com `&`: Diego & Victor Hugo; 9 com `e`: Felipe e Rodrigo)
    e protege esses nomes antes de splittar por `&`
  - Normalização cross-platform: case-insensitive + `&` ↔ `e`
  - Presença binária: artista ≥1 aparição no mês = presente

#### Resultados
- **Spotify:** 420 artistas únicos → JAN=293, FEV=324, MAR=326 → **210 persistentes** (3 meses)
- **YouTube:** 329 artistas únicos → JAN=208, FEV=192, MAR=216 → **104 persistentes** (3 meses)
- **Interseção cross-platform:** Só Spotify=139, Só YouTube=33, **★ Interseção=71**
- Spot-check ✅: Pedro Sampaio, Diego & Victor Hugo, MC Ryan SP, Vitinho Imperador,
  Henrique & Juliano, Grupo Menos É Mais, Felipe e Rodrigo, Taylor Swift

#### Bug Fix Detectado e Corrigido
- Duplas com `e` no Spotify (ex: `Felipe e Rodrigo`) não eram reconhecidas
  como duplas para proteger no YouTube (que usa `Felipe & Rodrigo`)
- Fix: `_extract_known_duos()` agora gera variante `&` de duos com `e`
- Resultado: 70 → **71** artistas na interseção (Felipe e Rodrigo adicionado)

#### CSVs Gerados
- `data/processed/spotify_persistent_artists.csv` — 210 artistas
- `data/processed/youtube_persistent_artists.csv` — 104 artistas
- `data/processed/cross_platform_persistent_artists.csv` — 71 artistas

#### Próximos Passos
1. Gerar novo `data/seed/artistas.csv` com os 71 artistas
2. Re-executar pipeline (youtube_collector → call2go_detector → DB → análises)
3. Análise comparativa COM vs SEM Call2Go
4. Caracterização de grupos
5. Investigar Call2Go reverso + Last.fm

#### Etapa 2: Detecção de Labels e Pipeline Completo (17-18/04/2026)
- **`chart_processor.py`** — Detecção de labels em 2 camadas:
  - Camada 1: regex keywords (`records`, `music`, `entertainment`, `ent`, `publishing`) + padrão artista veto + overrides
  - Removidos: Get Records (keyword), Get Worship (override), MJ Records (keyword), Supernova Ent (keyword)
  - **71 → 67 artistas**
- **`artist_source_builder.py`** — `build_seed_from_chart_intersection()`:
  - Resolve channel_id via YouTube Search API
  - Camada 2: avisos advisory (Torelli: 590 followers, sem gêneros)
- **Pipeline completo (12 etapas)** executado em 464.1s (7.7 min):
  - Step 1: Seed building — 67 artistas
  - Step 2: YouTube — 1.641 vídeos (30/artista max, 13 resumidos de runs anteriores)
  - Step 3: Spotify — 67/67 coletados (Pop range: 55-97)
  - Step 4: Channel scraping — 67 canais, 33 com Spotify, 9 OAC detectados (286.3s)
  - Step 5: Detecção Call2Go — 186 link_direto (11.3%), 1.455 nenhum (88.7%)
    - 174 auto-gerados (10.6%), 144 OAC (8.8%)
    - Fallback regex na bio do canal: +30 canais detectados via "Spotify - bit.ly/..."
  - Step 6: DB build — call2go.db (3 tabelas)
  - Step 7: EDA — link_direto média 8.6M views vs nenhum 14M
  - Step 8: Mann-Whitney — U=141605, p=0.151 — **NÃO REJEITA H0**
  - Step 9: Cross-platform — U=141582.5, p=0.999 — **NÃO REJEITA H0**
  - Step 10: Amostra — 50 vídeos (seed=42)
  - Step 11: Bidirecional — UNIDIRECIONAL Spotify→YouTube (ρ=0.508***, α=0.1)
  - Step 12: Census Excel — 1.641 vídeos com dropdowns SIM/NÃO

#### Outputs Gerados (18/04/2026)
- `data/seed/artistas.csv` — 67 artistas com channel_id
- `data/raw/youtube_videos_raw.jsonl` — 1.641 vídeos
- `data/raw/spotify_metrics_2026-04-18.csv` — 67 artistas
- `data/raw/channel_links_scraped.json` — 67 canais + 9 OAC
- `data/processed/youtube_call2go_flagged.csv` — 1.641 vídeos flagados
- `data/processed/call2go.db` — SQLite (3 tabelas)
- `data/plots/boxplot_call2go_views.png` — Boxplot views por tipo
- `data/plots/scatter_cross_platform.png` — Scatter cross-platform
- `data/validation/blind_annotation_census.csv` — Census CSV (1.641 vídeos)
- `data/validation/blind_annotation_census.xlsx` — Census Excel com dropdowns
- `data/validation/detector_answers_census.csv` — Respostas do detector
- `data/validation/direction_a_youtube_to_spotify.png` — Direção A
- `data/validation/direction_b_spotify_to_youtube.png` — Direção B
- `data/validation/bidirectional_correlation_matrix.png` — Heatmap

### 🟨 Pendente (Em Ordem de Prioridade)
1. [P0] 🔴 **Anotar 1.641 vídeos** em `blind_annotation_census.xlsx` (SIM/NÃO) → ground truth
2. [P1] Rodar `python -m src.validation.cross_validator` para validação censitária
3. [P2] 🔴 **Alinhar com orientador** sobre resultados e próximos passos
4. [P3] Escrever capítulo de Metodologia do TCC
5. [P4] Escrever capítulo de Resultados com Kappa 3 níveis + IC 95%

### ✅ Concluído (Fase 9c — Limpeza e Consistência, 12/04/2026)

#### Correções de Lógica
- **Combinado OR → AND** em 3 arquivos: `call2go_detector.py`, `cross_validator.py`, `blind_annotator.py`
  - Antes: combinado = vídeo OU canal (OR) — inflava taxa para 58.3%
  - Agora: combinado = vídeo E canal (AND) — interseção real
- **Normalização de canal via seed:** detecção de canal agora usa `artistas.csv` como fonte primária
  - Prioridade: canal oficial do seed → fallback pelo channel_id do JSONL
  - Resolve mismatch Anitta: seed `UCqjjyPUghDSSKFBABM_CXMw` (com Spotify) vs JSONL `UCtumXDPrqd3lhGEVyIex1lw` (sem)
- **excel_formatter.py:** instruções README corrigidas ("OU" → "E", removida referência a ground_truth_prefilled.csv)

#### Depreciação
- `ground_truth_helper.py` marcado como DEPRECATED (causa validação circular, Fase 8 audit)
  - Docstring de aviso + `warnings.warn(DeprecationWarning)` adicionados
  - Mantido como evidência de auditoria

#### Memory Bank
- `activeContext.md` reescrito com estado atual (12/04/2026)
- `systemPatterns.md` atualizado: tabela ETL, dados Fase 9, lógica AND
- `techContext.md` atualizado: datas corrigidas, listagem de arquivos atualizada
- `progress.md` atualizado: sumário executivo no topo, Fase 9c adicionada
- `projectbrief.md` ajustado: "~50 recentes" → "20 mais visualizados", playlists

#### Limpeza
- Removido `data/raw/spotify_metrics_2026-03-30.csv` (superseded)
- Artefatos regenerados: flagged CSV, DB, plots, censo XLSX

### ✅ Concluído (Fase 9 — Re-execução + Censo Completo, 11/04/2026)

#### Re-execução do Pipeline
- Pipeline completo re-executado do zero: 11 etapas em 5.6 min
- Playlists Spotify hardcoded (Top 50 Brasil, Viral 50, Top Hits) retornaram 404
- Fallback dinâmico encontrou 5 playlists alternativas → 340 candidatos únicos
- Filtro: popularity ≥ 60, canal YouTube válido → 217 candidatos → Top 50 por views
- **920 vídeos** coletados (20 mais visualizados × 46 artistas com vídeos)
- 51 canais scrapeados, métricas Spotify atualizadas (2026-04-11)

#### Adaptação para Censo Completo
- `blind_annotator.py`: nova função `generate_census_csv()` — lê TODOS os vídeos do JSONL (não apenas amostra)
- `excel_formatter.py`: novo modo `census_mode=True` com dropdowns SIM/NÃO binários
- Ambos suportam `--census` na CLI
- cross_validator.py já aceitava formato SIM/NÃO via `_map_to_binary()` (sem mudanças)

#### Artefatos Gerados
- `data/validation/blind_annotation_census.csv` — 920 vídeos, 46 artistas, 12 colunas
- `data/validation/blind_annotation_census.xlsx` — XLSX formatado com dropdowns SIM/NÃO, aba README, freeze panes
- Todos os 12 outputs do pipeline regenerados (ver relatório final)
- 77 testes passando
- Commit `653f3e9`, push OK

### ✅ Concluído (Fase 7 — Auditoria Profissional, 07/04/2026)

#### Problemas Críticos Encontrados
- **VALIDAÇÃO CIRCULAR CONFIRMADA:** ground_truth.csv é byte-a-byte idêntico ao ground_truth_prefilled.csv
  - SHA256 ambos: C5BC1124118A67BDF5FB94190DB09B19B852C4FC2D3D5B0DEC87A1501FC3F437
  - cross_validator.py comparava detector consigo mesmo → 100% acurácia por construção
  - Cohen's Kappa Nível 2-3 = 1.0 (circular) vs Nível 1 = 0.27 (honesto, "razoável")
- **ZERO texto_implicito no dataset real:** padrões existem no código mas nunca disparam em 980 vídeos
- **Amostra original enviesada:** 50 vídeos, 72% com auto_source=canal (trivial), 0 OAC, 0 redirect sem label, 0 narrativa

#### Soluções Implementadas
1. **tests/test_call2go_detector.py** — 77 testes adversariais em 11 grupos (100% passam)
2. **src/validation/adversarial_sampler.py** — Amostra estratificada de 91 vídeos cobrindo todos os edge cases
3. **src/validation/blind_annotator.py** — CSV cego v2:
   - +`youtube_channel_url` (URL do canal do artista)
   - +`channel_bio` substituiu `channel_description` (descrição + links da aba Sobre scrapeados)
   - Fallback por `artist_name` para channel_id mismatches (Anitta, Panda, etc.)
   - Resultado: 91/91 com links, 56/91 com Spotify na bio, 0 ausentes
4. **src/validation/excel_formatter.py** — NOVO: Gera Excel formatado (.xlsx) para anotação humana
   - Cabeçalho azul escuro, colunas de dados cinza, colunas de anotação amarelo
   - Dropdowns (link_direto/texto_implicito/nenhum), freeze panes, zebra striping
   - Aba README com instruções de preenchimento
   - Dependência: openpyxl==3.1.5
5. **cross_validator.py atualizado** — Cohen's Kappa + Bootstrap IC 95% + suporte a formato novo
6. **agreement_report.py atualizado** — Kappa + IC no resumo
7. **requirements.txt** — Todas as versões pinadas + scikit-learn + openpyxl + pytest adicionados
8. **Encoding fix** — 14 arquivos: emojis/caracteres não-cp1252 substituídos por ASCII
   - Pipeline agora roda sem PYTHONIOENCODING no Windows

#### Dados da Amostra Adversarial (91 vídeos)
- video_link_direto: 15 | ambos_link_direto: 10 | canal_only: 20
- nenhum_limpo: 15 | auto_generated: 10 | desc_vazia: 10 | desc_curta: 10
- narrativa_spotify: 1 | fallback_spotify: 0

### 🔲 Pendente (Melhorias Futuras)
- Coleta longitudinal do Spotify (múltiplas datas)
- Análise de engagement rate (likes/views, comments/views)
- Expansão do detector para outras plataformas (Deezer, Apple Music)
- Considerar scraping de perfis Spotify para links YouTube (Direção B real)

## Observações Importantes
- **Dados atuais:** 49 artistas Top 50 BR (MJ Records removido), 980 vídeos (20 mais visualizados/artista)
- **⚠️ Questão metodológica:** Direção B da validação bidirecional usa apenas correlação estatística, não links reais do Spotify→YouTube
- **⚠️ Mann-Whitney p=0.36:** Não há diferença significativa de views entre vídeos com/sem Call2Go — dado importante para discussão no TCC
- Pipeline 100% reprodutível: `python run_pipeline.py` executa todos os 11 passos
