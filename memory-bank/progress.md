# Progress -- TCC Call2Go

## Estado Atual (26/04/2026)
- Pipeline 16 etapas funcionando (67 artistas, 1.641 videos)
- Ranking Fusion v3.0: 288 artistas primarios, RRF normalizado, taxonomia estrutural 6 categorias
- 39/67 artistas seed encontrados como primarios nos charts Q1 2026
- Validacao baseline definitiva: Kappa=0.45 video / 0.80 canal (Fase 8)
- Census annotation formalmente descontinuado (26/04/2026)
- Last.fm integrado: 67/67 artistas, bridge analysis, charts BR 200+200
- Auditoria de voltas: 0 links reversos em todas as 4 direcoes

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

### Auditoria de Voltas Automatizada (21/04/2026)
- Script `src.validation.reverse_links_audit` implementado com Playwright
- Saidas: `cross_platform_reverse_links_audit.csv` + `cross_platform_reverse_links_summary.json`
- Cobertura: Spotify 67/67, Last.fm 67/67
- Direcoes auditadas: Spotify->YouTube, Spotify->Last.fm, Last.fm->YouTube, Last.fm->Spotify
- Resultado: todas as direcoes com contagem zero (0/67), sem erros de coleta
- Decisao: manter eixo analitico principal em efetividade cross-platform por popularidade e Call2Go YouTube->Spotify

### Fechamento End-to-End + Reprodutibilidade (22/04/2026)
- Pipeline completo executado do zero (step 1-14): 14/14 OK
- Ajuste de determinismo: `run_pipeline.py` recebeu flag `--force-channel-scrape`; padrao agora usa cache na etapa 5
- Efeito: remove variacao inter-run do scraping de canais e estabiliza metricas derivadas
- Last.fm bridge: removido warning de `ConstantInputWarning` no ranking comparativo
- Metricas recentes (cache-first):
	- Detector combinado: 88/1641 (5.4%)
	- Mann-Whitney views: U=73010, p=0.13970 (n.s.)
	- Bridge intersecao 3 fontes: 9/67 (13.4%)
	- Chi2 Call2Go vs Hit: X2=2.610, p=0.1062 (n.s.)
	- Genero x Call2Go: X2=2.293, p=0.6821 (n.s.)

### Fase 11 -- Ranking Fusion v3.0 (26/04/2026)
- Refatoracao completa de `src/analytics/ranking_fusion.py`
- 7 fases de refatoracao: seed matching, seed-only scope, RRF normalizacao,
  taxonomia estrutural 6 categorias, rank_delta variavel continua,
  top 75 heatmap, relatorio de metodologia
- **288 artistas primarios** (sem featured-only injetados; original 316 -> 288)
- **39/67 artistas seed** encontrados como primarios nos charts
- `score_X_normalized = score_X / n_semanas_plataforma` (antes de somar)
- Taxonomia: absent|single|persistent|new|exit|intermittent
- Top 1: PEDRO SAMPAIO score_combined=0.365385
- Commit: `8b3112a` | pushed para master
- Schema v3.0: 29 colunas em `data/processed/ranking_fusion_scores.csv`

### Fase 12 -- Governanca v3.1 (26/04/2026) [EM ANDAMENTO]
- [ ] Memory bank full restructure (todos os 6 arquivos)
- [ ] Pipeline governance (docstring 17 etapas, steps deprecated, step_17)
- [ ] Cross-validator formalization (docstring baseline definitivo)
- [ ] `src/validation/regex_audit.py` (novo modulo)
- [ ] `src/analytics/chart_temporal_analysis.py` (novo modulo, pergunta orientador)

## Pendente
1. [P0] **chart_temporal_analysis.py** -- pergunta orientador: YouTube precede Spotify charts?
2. [P1] **regex_audit.py** -- auditoria automatizada do detector (breakdown por regra)
3. [P2] **Alinhar com orientador** sobre resultados bridge + ranking fusion + temporal
4. [P3] Capitulos Metodologia + Resultados do TCC (LaTeX)
