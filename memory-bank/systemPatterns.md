# System Patterns -- TCC Call2Go

## Pipeline (12 Etapas)
`
1. Seed building (chart_processor + artist_source_builder)
2. YouTube collection (youtube_collector)
3. Spotify collection (spotify_collector)
4. Channel scraping (channel_link_scraper)
5. Call2Go detection (call2go_detector) -- regex multi-layer
6. DB build (db_builder) -- SQLite star schema
7. EDA (eda_analysis) -- boxplots, stats descritivas
8. Hypothesis testing (hypothesis_testing) -- Mann-Whitney U
9. Cross-platform analysis (spotify_impact_analysis)
10. Sample generation (sample_generator) -- 50 videos, seed=42
11. Bidirectional validation (cross_platform_validator)
12. Census Excel (blind_annotator + excel_formatter) -- dual output
`

## Deteccao Call2Go (3 niveis)
1. **Video:** regex na descricao (open.spotify.com, spoti.fi, sptfy.com, bit.ly labeled, CTA text)
2. **Canal (scraped):** links estruturados da aba Sobre (web scraping)
   - Fallback: regex na bio do canal (captura "Spotify - bit.ly/...")
3. **Combinado:** AND -- video E canal devem ter Call2Go

## Schema SQLite
`
dim_artist (artist_name PK, spotify_id, youtube_channel_id)
fact_yt_videos (video_id, artist_name FK, view_count, call2go_type, ...)
fact_spotify_metrics (date, spotify_id FK, followers, popularity)
`

## Convencoes
- Python 3, variaveis em ingles, comentarios em portugues
- Scripts standalone com `if __name__ == "__main__"`
- Dados: seed/ -> raw/ -> processed/ -> plots/ -> validation/
- Graficos DPI 300, figsize max 6x4 (1800x1200px)
- Pipeline encoding cp1252-safe (sem emojis no console)
- Dual Excel: blind (dropdowns) + detector answers (readonly)

## Validacao Estatistica
- Cohen's Kappa + Bootstrap CI 95% (2000 reamostras, seed=42)
- 3 niveis: video, canal, combinado
- Landis & Koch interpretacao automatica
- Mann-Whitney U (nao parametrico), alpha=0.05
