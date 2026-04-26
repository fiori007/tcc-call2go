# System Patterns — TCC Call2Go

## Pipeline (16 Etapas + 1 Pendente)
```
 1. Seed building (chart_processor + artist_source_builder)
 2. YouTube collection (youtube_collector)
 3. Spotify collection (spotify_collector)
 4. Last.fm collection (lastfm_collector + lastfm_chart_collector) -- artistas + charts BR
 5. Channel scraping (channel_link_scraper) -- cache-first por padrao
 6. Call2Go detection (call2go_detector) -- regex multi-layer 3 niveis
 7. DB build (db_builder) -- SQLite star schema (6 tabelas), batch/rebuild
 8. EDA (eda_analysis) -- boxplots, stats descritivas
 9. Hypothesis testing (hypothesis_testing) -- Mann-Whitney U
10. Cross-platform analysis (spotify_impact_analysis) -- bidirecional
11. Last.fm Bridge (lastfm_bridge_analysis) -- 8 analises 3 fontes
12. [DEPRECATED 26/04/2026] Sample generation (sample_generator) -- validacao manual descontinuada
13. Bidirectional validation (cross_platform_validator) -- YouTube <-> Spotify
14. [DEPRECATED 26/04/2026] Census Excel (blind_annotator + excel_formatter) -- anotacao manual descontinuada
15. Spotify track dates collection (spotify_track_dates_collector)
16. Ranking Fusion v3.0 (ranking_fusion) -- RRF normalizado, 288 artistas, taxonomia estrutural
17. [PENDING] Chart Temporal Analysis (chart_temporal_analysis) -- pergunta do orientador
```

## Decisao Arquitetural: DB Builder (batch/rebuild)
- **Decisao:** DROP + recreate completo a cada execucao (nao incremental)
- **Justificativa:** reproducibilidade analitica > eficiencia de escrita;
  SQLite e artefato de pesquisa (nao producao); rebuild < 1s; sem concorrencia.
- **Serie temporal:** Spotify + Last.fm concatenam todos os snapshots + dedup por (date, id).
  Permite rastrear evolucao de metricas ao longo das coletas.

## Determinismo / Cache
- Etapa 5 (scraping de canais) opera em cache-first por padrao para estabilidade entre reruns.
- Flag de override no pipeline: `--force-channel-scrape` (ignora cache e re-scrapa).
- Objetivo: reduzir variacao estocastica de disponibilidade de pagina e garantir reprodutibilidade analitica.

## Auditoria de Voltas (metodologica)
- Script standalone: `src.validation.reverse_links_audit` (Playwright)
- Escopo: Spotify->YouTube, Spotify->Last.fm, Last.fm->YouTube, Last.fm->Spotify
- Cobertura validada: 67/67 em ambas plataformas
- Resultado: 0 ocorrencias em todas as direcoes

## Deteccao Call2Go (3 niveis, 6 regras + guard narrativo)

### Nivel 1 -- Video (regex na descricao)
| Regra | Padrao | Risco FP |
|-------|--------|----------|
| R1 | `open.spotify.com / spoti.fi / sptfy.com` | Baixo (URL literal) |
| R2 | `spotify: https://url` (labeled redirect) | Baixo (label + URL) |
| R3 | `https://...*spotify*` no path | Medio |
| R4 | `ouca/disponivel/stream... spotify` (CTA text) | Baixo |
| R5 | `\bspotify\b` (fallback) | ALTO -- mais liberal |
| G | `_is_narrative_mention()` (guard) | Supressor de FP |

### Nivel 2 -- Canal (links scrapeados da aba Sobre + fallback regex na bio)
- Fonte primaria: `channel_links_scraped.json` (web scraping da About page)
- Fallback: regex na bio do canal captura `"Spotify - bit.ly/..."` que o scraper nao ve
- OAC (auto-generated): verifica canal oficial linkado pelo scraper

### Nivel 3 -- Combinado (AND)
- `has_call2go = video_has AND canal_has`
- Semantica: artista promove ativa e estruturalmente o Spotify (descricao + perfil)

## Schema ranking_fusion_scores.csv (v3.0, 26/04/2026)
```
artist_normalized        -- nome normalizado (NFKD, lowercase, sem pontuacao)
score_spotify            -- RRF raw Spotify (suma 1/rank por mes presente)
score_youtube            -- RRF raw YouTube
rank_Jan_sp, rank_Feb_sp, rank_Mar_sp  -- melhor rank mensal Spotify
rank_Jan_yt, rank_Feb_yt, rank_Mar_yt  -- melhor rank mensal YouTube
presence_count_spotify   -- numero de meses presente no Spotify (0-3)
presence_count_youtube   -- numero de meses presente no YouTube (0-3)
presence_vector_str_spotify/youtube -- vetor binario '(1,0,1)'
global_rank_spotify/youtube/combined -- posicao global por score
in_dataset               -- True se artista primario nos charts AND seed
artist_name_seed         -- nome original do artista.csv (se in_dataset)
score_spotify_normalized -- score_spotify / n_semanas_spotify
score_youtube_normalized -- score_youtube / n_semanas_youtube
score_combined           -- soma dos scores normalizados
pattern_spotify/youtube  -- absent|single|persistent|new|exit|intermittent
rank_delta_spotify/youtube -- rank_Jan - rank_Mar (int; None se algum ausente)
first_chart_week_spotify/youtube -- data da primeira semana nos charts
total_weeks_spotify/youtube  -- numero total de semanas nos charts Q1 2026
```

## Schema SQLite (6 tabelas)
dim_artist (artist_name PK, spotify_id, youtube_channel_id)
fact_yt_videos (video_id, artist_name FK, view_count, call2go_type, ...)
fact_spotify_metrics (date, spotify_id FK, followers, popularity)
fact_lastfm_metrics (date, artist_name FK, listeners, playcount, tags, top tracks)
fact_lastfm_chart_artists (date, rank, artist_name, listeners, chart_country)
fact_lastfm_chart_tracks (date, rank, track_name, artist_name, listeners, chart_country)
```

## Convencoes
- Python 3, variaveis em ingles, comentarios em portugues
- Scripts standalone com `if __name__ == "__main__"`
- Dados: seed/ -> raw/ -> processed/ -> plots/ -> validation/
- Graficos DPI 300, figsize max 6x4 (1800x1200px)
- Pipeline encoding cp1252-safe (sem emojis no console)

## Validacao Baseline Definitiva (Fase 8, 10/04/2026)
- **Metodo:** 91 videos adversariais, anotacao cega, sem contaminacao
- **Kappa video:** 0.45 (moderado) | IC 95% Bootstrap 2000 reamostras
- **Kappa canal:** 0.80 (substancial) | IC 95% Bootstrap 2000 reamostras
- **Acuracia video:** 82.4% | Acuracia canal: 90.1%
- ground_truth.csv removido 18/04/2026; census descontinuado 26/04/2026
- Detector opera em modo confiado (6 iteracoes de auditoria)
