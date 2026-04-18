# Active Context — TCC Call2Go

## Estado Atual (18/04/2026 — Fase 10: Pipeline Completo Executado)
Pipeline completo de 12 etapas executado com sucesso para a nova base temporal.
67 artistas consolidados (71 interseção - 4 labels detectados automaticamente).
1.641 vídeos coletados, detecção Call2Go aplicada, análises estatísticas geradas,
Census Excel para validação manual gerado.

**Resultado: ★ 67 artistas × até 30 vídeos = 1.641 vídeos analisados**

## Detecção de Labels (2 camadas)
- **Camada 1 (`chart_processor.py`):** regex keywords + padrão artista veto + overrides
  - Removidos: Get Records (keyword), Get Worship (override), MJ Records (keyword), Supernova Ent (keyword)
- **Camada 2 (`artist_source_builder.py`):** avisos advisory para entidades suspeitas
  - Torelli flagado (590 followers, sem gêneros) — apenas informativo, não excluído
- **71 → 67 artistas** após remoção de labels

## Dados Atuais
- **Seed:** `data/seed/artistas.csv` — 67 artistas com channel_id YouTube
- **YouTube:** `data/raw/youtube_videos_raw.jsonl` — 1.641 vídeos (30/artista max)
- **Spotify:** `data/raw/spotify_metrics_2026-04-18.csv` — 67 artistas coletados
- **Scraping:** `data/raw/channel_links_scraped.json` — 67 canais + 9 OAC oficiais
  - 33/67 com Spotify no perfil, 9 OAC detectados
- **Detecção:** `data/processed/youtube_call2go_flagged.csv` — 1.641 vídeos flagados
  - link_direto: 168 (10.2%), nenhum: 1.473 (89.8%)
  - Vídeos auto-gerados: 174 (10.6%), Canais OAC: 144 (8.8%)
- **DB:** `data/processed/call2go.db` — SQLite com 3 tabelas
- **Plots:** boxplot_call2go_views.png, scatter_cross_platform.png
- **Validação:** Dual Census Excel (padrão do projeto):
  - `blind_annotation_census.xlsx` — versão cega para humano anotar (dropdowns SIM/NAO, colunas vazias)
  - `detector_answers_census.xlsx` — gabarito do detector (SIM/NAO preenchido, sem dropdowns)
  - Distribuição detector: Video 11.9% SIM, Canal 52.5% SIM, Combinado 10.2% SIM

## Resultados Estatísticos (Pipeline 18/04/2026)
- **Mann-Whitney (Views):** U=129940, p=0.143 — **NÃO REJEITA H0**
- **Cross-Platform:** U=138828.5, p=0.986 — **NÃO REJEITA H0**
- **Bidirecional:** UNIDIRECIONAL Spotify → YouTube (α=0.1)
  - Direção A (YT→Spotify): Call2Go Rate ↔ Pop ρ=-0.079, p=0.525 — NÃO significativo
  - Direção B (Spotify→YT): Pop ↔ Avg Views ρ=0.508, p≈0*** — SIGNIFICATIVO
  - Followers ↔ Avg Views ρ=0.676, p≈0*** — SIGNIFICATIVO

## Próximas Ações (Prioridade)
1. [P0] 🔴 **Anotar 1.641 vídeos** em `blind_annotation_census.xlsx` (SIM/NÃO) → salvar como `ground_truth.csv`
2. [P1] Rodar `python -m src.validation.cross_validator` para validação censitária
3. [P2] 🔴 **Alinhar com orientador** sobre resultados
4. [P3] Escrever capítulo de Metodologia do TCC
5. [P4] Escrever capítulo de Resultados com Kappa 3 níveis + IC 95%
