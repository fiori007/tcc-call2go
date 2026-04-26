# Active Context — TCC Call2Go v3.1

## Estado Atual (26/04/2026)
Pipeline 16 etapas executado com sucesso. Base temporal Q1 2026 consolidada.
Ranking fusion refatorado (v3.0, 26/04/2026): escopo primarios, RRF normalizado, taxonomia estrutural.
**Foco atual: modulos ranking + analise temporal (pergunta do orientador sobre datas/defasagem).**
**67 artistas x 30 videos = 1.641 videos analisados.**
**Last.fm integrado: 67/67 artistas (100%), charts BR 200+200, bridge analysis 8 analises.**

## Dados em Uso
| Arquivo | Conteudo |
|---------|----------|
| `data/seed/artistas.csv` | 67 artistas com channel_id |
| `data/raw/youtube_videos_raw.jsonl` | 1.641 videos brutos |
| `data/raw/spotify_metrics_2026-04-22.csv` | 67 artistas (metricas mais recentes) |
| `data/raw/lastfm_artists_2026-04-22.csv` | 67 artistas Last.fm (listeners, scrobbles, tags) |
| `data/raw/lastfm_top_tracks_2026-04-22.csv` | 659 tracks (top 10 por artista) |
| `data/raw/channel_links_scraped.json` | 75 canais (67 + 9 OAC oficiais) -- cache-first |
| `data/processed/youtube_call2go_flagged.csv` | 1.641 videos com flags Call2Go |
| `data/raw/lastfm_chart_artists_brazil_2026-04-22.csv` | Top 200 artistas BR Last.fm |
| `data/raw/lastfm_chart_tracks_brazil_2026-04-22.csv` | Top 200 tracks BR Last.fm |
| `data/raw/spotify_charts/*.csv` | 13 semanas Spotify BR Top 200 (Q1 2026) -- ESTATICO |
| `data/raw/youtube_charts/*.csv` | 13 semanas YouTube BR Top 100 (Q1 2026) -- ESTATICO |
| `data/raw/spotify_track_dates_Q1_2026.csv` | Datas de lancamento das faixas dos charts |
| `data/processed/ranking_fusion_scores.csv` | 288 artistas, RRF normalizado v3.0 |
| `data/processed/call2go.db` | SQLite (6 tabelas: +chart_artists, +chart_tracks) |
| `data/validation/seed_matching_diagnostic.csv` | 67 artistas seed: primario/featured/nao-encontrado |
| `data/validation/temporal_lag_results.csv` | Lag temporal release Spotify vs primeiro Call2Go YT (6 artistas) |
| `data/validation/cross_platform_reverse_links_audit.csv` | Auditoria automatizada de voltas (67 artistas) |

## Distribuicao Detector (rerun completo cache-first, 22/04/2026)
| Nivel | SIM | NAO |
|-------|-----|-----|
| Video | 196 (11.9%) | 1.445 (88.1%) |
| Canal | 410 (25.0%) | 1.231 (75.0%) |
| Combinado (AND) | 88 (5.4%) | 1.553 (94.6%) |

## Validacao do Detector (DEFINITIVA -- Fase 8, 10/04/2026)
- **Metodo:** Anotacao humana cega (91 videos adversariais, sem viés de confirmacao)
- **Kappa video:** 0.45 (moderado) com IC 95% Bootstrap
- **Kappa canal:** 0.80 (substancial) com IC 95% Bootstrap
- **Acuracia video:** 82.4% | **Acuracia canal:** 90.1%
- **ground_truth.csv:** removido no cleanup de 18/04/2026
- **Census annotation (1641 videos):** DESCONTINUADO em 26/04/2026
- **Decisao:** Detector opera em modo confiado. Confianca elevada incrementalmente por 6 iteracoes de auditoria e fixe de bugs. Sem necessidade de nova validacao manual.

## Ranking Fusion v3.0 (26/04/2026)
- **288 artistas primarios** nos charts Q1 2026 (de 316, sem featured-only)
- **39 do seed** (67) encontrados como primarios nos charts
- **RRF normalizado:** score_X / n_semanas antes de somar (Spotify=13, YouTube=13)
- **Taxonomia estrutural:** 6 categorias (absent/single/persistent/new/exit/intermittent)
- **rank_delta:** variavel continua Jan-Mar (sem threshold)
- **score_combined:** max=0.365385, mediana=0.002072
- Top 1: PEDRO SAMPAIO (0.365385) | Top 2: DJ Japa NK (0.352564)

## Resultados Estatisticos (estavel desde 22/04/2026)
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
- **Resultado:** 0 links reversos em todas as 4 direcoes
- **Conclusao:** sem evidencias de volta por links de perfil

## Proximas Acoes
1. [DONE] ~~Analise cross-platform 3 fontes (YouTube x Spotify x Last.fm)~~
2. [DONE] ~~Ranking Fusion v3.0 (288 artistas, RRF normalizado, taxonomia estrutural)~~
3. [DONE] ~~Census annotation~~ -- DESCONTINUADO 26/04/2026
4. [P0] **chart_temporal_analysis.py** -- pergunta do orientador: YouTube precede Spotify?
5. [P1] **regex_audit.py** -- auditoria automatizada do detector (breakdown por regra)
6. [P2] **Alinhar com orientador** sobre resultados bridge + analise temporal
7. [P3] Escrever capitulos Metodologia + Resultados do TCC (LaTeX, demanda posterior)
