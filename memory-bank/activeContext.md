# Active Context — TCC Call2Go

## Estado Atual (18/04/2026)
Pipeline 12 etapas executado com sucesso. Base temporal Q1 2026 consolidada.
**67 artistas x 30 videos = 1.641 videos analisados.**

## Dados em Uso
| Arquivo | Conteudo |
|---------|----------|
| `data/seed/artistas.csv` | 67 artistas com channel_id |
| `data/raw/youtube_videos_raw.jsonl` | 1.641 videos brutos |
| `data/raw/spotify_metrics_2026-04-18.csv` | 67 artistas (metricas atuais) |
| `data/raw/channel_links_scraped.json` | 75 canais (67 + 9 OAC oficiais) |
| `data/processed/youtube_call2go_flagged.csv` | 1.641 videos com flags Call2Go |
| `data/processed/call2go.db` | SQLite (dim_artist, fact_yt_videos, fact_spotify) |

## Distribuicao Detector
| Nivel | SIM | NAO |
|-------|-----|-----|
| Video | 196 (11.9%) | 1.445 (88.1%) |
| Canal | 891 (54.3%) | 750 (45.7%) |
| Combinado (AND) | 186 (11.3%) | 1.455 (88.7%) |

## Resultados Estatisticos
- **Mann-Whitney (Views):** U=141605, p=0.151 -- NAO REJEITA H0
- **Cross-Platform:** U=111388, p=0.999 -- NAO REJEITA H0
- **Bidirecional:** UNIDIRECIONAL Spotify -> YouTube (alpha=0.1)
  - Direcao A: Call2Go Rate <-> Pop rho=-0.111, p=0.370 -- n.s.
  - Direcao B: Pop <-> Avg Views rho=0.508, p~0*** | Followers <-> Avg Views rho=0.676, p~0***

## Proximas Acoes
1. [P0] **Anotar 1.641 videos** em `blind_annotation_census.xlsx` -> salvar como `ground_truth.csv`
2. [P1] Rodar `python -m src.validation.cross_validator` (Kappa + Bootstrap CI 3 niveis)
3. [P2] **Alinhar com orientador** sobre resultados
4. [P3] Escrever capitulos Metodologia + Resultados do TCC
