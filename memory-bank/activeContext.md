# Active Context — TCC Call2Go

## Estado Atual (19/04/2026)
Pipeline 14 etapas executado com sucesso. Base temporal Q1 2026 consolidada.
**67 artistas x 30 videos = 1.641 videos analisados.**
**Last.fm integrado: 67/67 artistas (100%), charts BR 200+200, bridge analysis 8 analises.**

## Dados em Uso
| Arquivo | Conteudo |
|---------|----------|
| `data/seed/artistas.csv` | 67 artistas com channel_id |
| `data/raw/youtube_videos_raw.jsonl` | 1.641 videos brutos |
| `data/raw/spotify_metrics_2026-04-18.csv` | 67 artistas (metricas atuais) |
| `data/raw/lastfm_artists_2026-04-18.csv` | 67 artistas Last.fm (listeners, scrobbles, tags) |
| `data/raw/lastfm_top_tracks_2026-04-18.csv` | 659 tracks (top 10 por artista) |
| `data/raw/channel_links_scraped.json` | 75 canais (67 + 9 OAC oficiais) |
| `data/processed/youtube_call2go_flagged.csv` | 1.641 videos com flags Call2Go |
| `data/raw/lastfm_chart_artists_brazil_2026-04-19.csv` | Top 200 artistas BR Last.fm |
| `data/raw/lastfm_chart_tracks_brazil_2026-04-19.csv` | Top 200 tracks BR Last.fm |
| `data/validation/three_source_profile.csv` | Perfil 3 fontes por artista |
| `data/validation/lastfm_bridge_report.txt` | Relatorio consolidado bridge |
| `data/processed/call2go.db` | SQLite (6 tabelas: +chart_artists, +chart_tracks) |

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

### Last.fm Bridge (3 Fontes) -- 19/04/2026
- **Intersecao 3 fontes:** 8/67 (11.9%) no Top 200 BR
- **Ranking convergencia:** Last.fm Listeners <-> Scrobbles rho=0.951, Spotify Followers <-> Last.fm Scrobbles rho=0.845
- **Track matching:** 279/1641 (17%) matched top tracks, 22 (1.3%) chart BR
- **Call2Go vs Hit:** X2=2.032, p=0.154 -- NAO SIGNIFICATIVO
- **Mann-Whitney Last.fm:** Listeners p=0.573, Scrobbles p=0.702 -- NAO SIGNIFICATIVO
- **Call2Go Rate <-> Last.fm Listeners:** rho=-0.120, p=0.334 -- n.s.
- **Genero x Call2Go:** X2=4.255, p=0.373 -- NAO SIGNIFICATIVO

## Proximas Acoes
1. [P0 DONE] ~~Analise cross-platform 3 fontes (YouTube x Spotify x Last.fm)~~
2. [P1] **Anotar 1.641 videos** em `blind_annotation_census.xlsx` -> salvar como `ground_truth.csv`
3. [P2] Rodar `python -m src.validation.cross_validator` (Kappa + Bootstrap CI 3 niveis)
4. [P3] **Alinhar com orientador** sobre resultados Last.fm Bridge
5. [P4] Escrever capitulos Metodologia + Resultados do TCC
