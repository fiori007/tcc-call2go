# Active Context — TCC Call2Go v4.0

## Estado Atual (28/04/2026)
Pipeline v4.0: **15 etapas ativas** (deprecated steps removidos), clean-state run 100% OK.
Coluna `has_call2go_or` adicionada ao detector (OR = 518/1641 = 31.6%).
Todas as análises estatísticas (H2, H3, H4) usam OR como métrica primária + AND sub-análise.
**Projeto pronto para elaboração do artigo/TCC.**

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

## Distribuicao Detector (28/04/2026, pipeline v4.0 clean-state)
| Nivel | Logica | SIM | NAO |
|-------|--------|-----|-----|
| Video | - | 196 (11.9%) | 1.445 (88.1%) |
| Canal | - | 410 (25.0%) | 1.231 (75.0%) |
| Combinado AND | video E canal | 88 (5.4%) | 1.553 (94.6%) |
| **OR (primario)** | **video OU canal** | **518 (31.6%)** | **1.123 (68.4%)** |

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

## Resultados Estatisticos Definitivos (28/04/2026)
### H2 — Mann-Whitney Views vs Call2Go
- **OR primario:** U=280705, p=0.872 — NAO REJEITA H0 (n_or=518 vs n_ctrl=1123)
- **AND sub-analise:** U=73010, p=0.140 — NAO REJEITA H0 (n_and=88 vs n_ctrl=1553)

### H3 — Mann-Whitney Spotify Popularity vs Call2Go
- **OR primario:** p=1.000 — NAO REJEITA H0
- **AND sub-analise:** p=0.998 — NAO REJEITA H0
- Bidirecional: UNIDIRECIONAL Spotify -> YouTube (direcao A: p~0.95 n.s.; direcao B: rho=0.505 p~0***)

### H4 — Lag Temporal + Correlacoes Spearman (n=39 artistas seed)
- **lag_any_days:** mediana=-882d IQR=[-1814, -360] (95% YouTube ativo antes do chart)
- **lag_call2go_days:** mediana=-824d IQR=[-1537, -296] (89% Call2Go antes do chart, n=18)
- **videos_30d_pre_chart x score_combined:** rho=0.364, p=0.022 * (SIGNIFICATIVO)
- **lag_call2go x score_spotify:** rho=0.028, p=0.913 n.s.
- **call2go_pre_chart x score_spotify:** rho=-0.093, p=0.575 n.s.

### Last.fm Bridge (3 Fontes) — 67 artistas
- Intersecao 3 fontes: 9/67 (13.4%) no Top 200 BR
- Spotify Followers <-> Last.fm Scrobbles: rho=0.848 ***
- Call2Go vs Hit status: X2=2.610, p=0.106 — n.s.
- Mann-Whitney Last.fm: listeners p=0.865, scrobbles p=0.960 — n.s.
- Genero x Call2Go: X2=2.293, p=0.682 — n.s.

### Auditoria de Voltas (21/04/2026)
- 67/67 Spotify, 67/67 Last.fm — 0 links reversos em 4 direcoes

## Proximas Acoes
1. [DONE] ~~Pipeline v4.0 (15 steps, OR logic, clean-state reproducibility)~~
2. [PENDING] Elaboração do artigo/TCC (aguardando instrução explícita)

4. [P0] **chart_temporal_analysis.py** -- pergunta do orientador: YouTube precede Spotify?
5. [P1] **regex_audit.py** -- auditoria automatizada do detector (breakdown por regra)
6. [P2] **Alinhar com orientador** sobre resultados bridge + analise temporal
7. [P3] Escrever capitulos Metodologia + Resultados do TCC (LaTeX, demanda posterior)
