# Active Context — TCC Call2Go

## Estado Atual (22/04/2026)
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
| `data/validation/cross_platform_reverse_links_audit.csv` | Auditoria automatizada de voltas (67 artistas) |
| `data/validation/cross_platform_reverse_links_summary.json` | Resumo de cobertura e contagens de voltas |
| `data/processed/call2go.db` | SQLite (6 tabelas: +chart_artists, +chart_tracks) |

## Distribuicao Detector (rerun completo cache-first)
| Nivel | SIM | NAO |
|-------|-----|-----|
| Video | 196 (11.9%) | 1.445 (88.1%) |
| Canal | 410 (25.0%) | 1.231 (75.0%) |
| Combinado (AND) | 88 (5.4%) | 1.553 (94.6%) |

## Resultados Estatisticos
- **Mann-Whitney (Views):** U=73010, p=0.13970 -- NAO REJEITA H0
- **Cross-Platform:** U=111388, p=0.999 -- NAO REJEITA H0
- **Bidirecional:** UNIDIRECIONAL Spotify -> YouTube (alpha=0.1)
  - Direcao A: Call2Go Rate <-> Pop rho=0.008, p=0.947 -- n.s.
  - Direcao B: Pop <-> Avg Views rho=0.505, p~0*** | Followers <-> Avg Views rho=0.674, p~0***

### Last.fm Bridge (3 Fontes) -- 22/04/2026
- **Intersecao 3 fontes:** 9/67 (13.4%) no Top 200 BR
- **Ranking convergencia:** Last.fm Listeners <-> Scrobbles rho=0.951, Spotify Followers <-> Last.fm Scrobbles rho=0.845
- **Track matching:** 279/1641 (17%) matched top tracks, 23 (1.4%) chart BR
- **Call2Go vs Hit:** X2=2.610, p=0.1062 -- NAO SIGNIFICATIVO
- **Mann-Whitney Last.fm:** listeners p=0.86466, scrobbles p=0.96003 -- NAO SIGNIFICATIVO
- **Call2Go Rate <-> Last.fm Listeners:** rho=-0.036, p=0.773 -- n.s.
- **Genero x Call2Go:** X2=2.293, p=0.6821 -- NAO SIGNIFICATIVO

### Auditoria de Voltas (Spotify/Last.fm) -- 21/04/2026
- **Cobertura automatizada:** 67/67 Spotify, 67/67 Last.fm
- **Spotify -> YouTube:** 0/67
- **Spotify -> Last.fm:** 0/67
- **Last.fm -> YouTube:** 0/67
- **Last.fm -> Spotify:** 0/67
- **Erros de coleta:** 0
- **Conclusao:** sem evidencias de "volta" por links de perfil; seguir foco em popularidade/correlacao cross-platform

### Reprodutibilidade -- 22/04/2026
- Pipeline rerodado 2x consecutivas do passo 1 ao 14 em modo cache-first
- Resultado operacional: 14/14 etapas OK em ambos os runs
- Resultado analitico: metricas-chave estaveis (detector, testes e bridge) nos dois runs
- Classificacao: reprodutibilidade **idêntica** sob mesma condicao de cache

## Proximas Acoes
1. [P0 DONE] ~~Analise cross-platform 3 fontes (YouTube x Spotify x Last.fm)~~
2. [P1] **Anotar 1.641 videos** em `blind_annotation_census.xlsx` -> salvar como `ground_truth.csv`
3. [P2] Rodar `python -m src.validation.cross_validator` (Kappa + Bootstrap CI 3 niveis)
4. [P3] **Alinhar com orientador** sobre resultados Last.fm Bridge + auditoria de voltas
5. [P4] Escrever capitulos Metodologia + Resultados do TCC
