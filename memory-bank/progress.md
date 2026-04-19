# Progress -- TCC Call2Go

## Estado Atual (19/04/2026)
- Pipeline 14 etapas funcionando (67 artistas, 1.641 videos)
- Last.fm integrado: 67/67 artistas (100%), 659 tracks, charts BR 200+200
- Last.fm Bridge analysis: 8 analises cross-platform 3 fontes
- DB SQLite com 6 tabelas: +fact_lastfm_chart_artists, +fact_lastfm_chart_tracks
- Codigo auditado, arquivos obsoletos removidos, caches limpos

## Historico Resumido

### Fases 1-4 (Marco/2026) -- Pipeline Original
- Coleta Spotify + YouTube, detector regex, DB SQLite, analises estatisticas
- Validacao cruzada humano vs maquina (50 videos amostra, seed=42)
- Ground truth helper descartado (validacao circular)

### Fases 5-6 (31/03/2026) -- Novo Pipeline Top 50 BR + Correcoes
- Pipeline reconstruido: 49 artistas (MJ Records removido), 980 videos
- 6 fixes no detector: redirect links (bit.ly, lnk.to, smarturl.it), greedy fix, labeled redirect
- Channel detection via web scraping (channel_link_scraper.py)

### Fase 8 (10/04/2026) -- Cross-Validation Real (91 videos adversariais)
- Anotacao humana cega: 91 videos, formato SIM/NAO
- Video: Kappa 0.45 (moderado), Acuracia 82.4%
- Canal: Kappa 0.80 (substancial), Acuracia 90.1%
- Combinado: Kappa 0.09 (fraco -- artefato AND vs OR, nao falha do detector)

### Fase 10 (16-18/04/2026) -- Nova Base Temporal Q1 2026
- Chart processor: 13 CSVs Spotify + 13 CSVs YouTube, Q1 2026
- Persistencia 3 meses: Spotify 210, YouTube 104, Intersecao 71
- Label detection (2 camadas): 71 -> 67 artistas
- Pipeline completo executado: 1.641 videos, 12 etapas

### Cleanup (18/04/2026)
- Removidos: adversarial_sampler.py, ground_truth_helper.py (deprecated)
- Removidos: spotify_metrics_2026-04-11.csv (snapshot antigo)
- Removidos: ground_truth.csv (fase 3 antiga, validacao circular)
- Fallback regex na bio do canal: +30 canais detectados (52.5% -> 54.3%)
- Caches __pycache__/ e .pytest_cache limpos

## Resultados Atuais (18/04/2026)
- Deteccao: 186 link_direto (11.3%), 1.455 nenhum (88.7%)
- Mann-Whitney: U=141605, p=0.151 -- NAO REJEITA H0
- Cross-platform: U=111388, p=0.999 -- NAO REJEITA H0
- Bidirecional: UNIDIRECIONAL Spotify -> YouTube

### Last.fm (18/04/2026)
- lastfm_collector.py criado (pattern = spotify_collector)
- 3 endpoints: getInfo (listeners, scrobbles, tags), getTopTracks, getTopAlbums
- 67/67 artistas encontrados, 659 tracks, 0 erros
- Integrado no pipeline (step 4) e DB (fact_lastfm_metrics)

### Last.fm Bridge Analysis (19/04/2026)
- lastfm_chart_collector.py: geo.getTopArtists + geo.getTopTracks (200+200 BR)
- lastfm_bridge_analysis.py: 8 analises cross-platform 3 fontes
- 8/67 artistas no Top 200 BR (11.9%): Taylor Swift, Marina Sena, Pedro Sampaio...
- Correlacoes fortes: Spotify Followers <-> Last.fm Scrobbles rho=0.845
- Call2Go vs Hit status: NAO significativo (p=0.154)
- Mann-Whitney Last.fm: NAO significativo (listeners p=0.573, scrobbles p=0.702)
- Genero x Call2Go: NAO significativo (p=0.373)
- Pipeline: step 4 coleta charts, step 11 roda bridge analysis
- DB: +fact_lastfm_chart_artists, +fact_lastfm_chart_tracks (6 tabelas total)

## Pendente
1. ~~[P0] Analise cross-platform 3 fontes~~ DONE
2. [P1] Anotar 1.641 videos (blind_annotation_census.xlsx)
3. [P2] Cross-validation censitaria (cross_validator.py)
4. [P3] Alinhar com orientador sobre resultados bridge
5. [P4] Capitulos Metodologia + Resultados do TCC
