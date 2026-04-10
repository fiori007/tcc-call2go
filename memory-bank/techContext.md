# Tech Context — TCC Call2Go

## Stack Principal
| Tecnologia | Versão | Uso |
|------------|--------|-----|
| Python | 3.12.9 | Linguagem principal |
| Pandas | 3.0.1 | Manipulação de dados |
| NumPy | 2.4.3 | Computação numérica |
| Spotipy | 2.23.0 | Wrapper da Spotify Web API |
| google-api-python-client | 2.97.0 | YouTube Data API v3 |
| Requests | 2.31.0 | HTTP requests |
| python-dotenv | 1.0.0 | Gerenciamento de env vars |
| SQLite3 | built-in | Data Warehouse local |
| Matplotlib | 3.10.8 | Visualização |
| Seaborn | 0.13.2 | Visualização estatística |
| SciPy | 1.17.1 | Testes estatísticos |
| statsmodels | 0.14.6 | Modelos estatísticos |
| scikit-learn | 1.8.0 | Cohen's Kappa (concordância inter-anotador) |
| openpyxl | 3.1.5 | Formatação Excel para anotação humana |
| pytest | 9.0.3 | Testes unitários adversariais |

## APIs Externas
- **Spotify Web API** — via OAuth2 Client Credentials (sem login do usuário)
  - Endpoint: artist metadata (followers, popularity)
  - Autenticação: `SPOTIFY_CLIENT_ID` + `SPOTIFY_CLIENT_SECRET`
- **YouTube Data API v3** — via API Key
  - Endpoints: channels, playlistItems, videos
  - Autenticação: `YOUTUBE_API_KEY`
  - **Otimização de quota:** `playlistItems.list` (1 unit) substituiu `search.list` (100 units) = 89% menos quota
  - Coleta: UC→UU (uploads playlist) → scan 200 vídeos → sort local por viewCount → top 20
  - Resume capability: lê JSONL existente, pula artistas já coletados
  - Quota: 10.000 units/dia, reset meia-noite Pacific Time (04:00 BRT)
  - Estimativa consumo: ~550 units para 50 artistas (vs. 5.150 antes)

## Configuração Necessária
Arquivo `.env` na raiz do projeto com:
```
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
YOUTUBE_API_KEY=...
```

## Dependências
As bibliotecas de análise são usadas nos scripts de analytics e validation:
- `matplotlib` — `eda_analysis.py`, `spotify_impact_analysis.py`, `cross_platform_validator.py`, `agreement_report.py`
- `seaborn` — `eda_analysis.py`, `spotify_impact_analysis.py`, `cross_platform_validator.py`
- `scipy` — `hypothesis_testing.py`, `spotify_impact_analysis.py`, `cross_platform_validator.py`

## Estrutura de Diretórios
```
tcc_call2go/
├── requirements.txt              # Todas as versões pinadas (12 dependências)
├── run_pipeline.py               # Orquestrador: 11 etapas, sem emojis (cp1252 safe)
├── .env                          # Credenciais (NÃO commitar)
├── .env.example                  # Template de credenciais
├── .gitignore                    # Python, venv, .env, LaTeX, SBC template, .db
├── data/
│   ├── seed/
│   │   └── artistas.csv              # 49 artistas (MJ Records removido)
│   ├── plots/                        # Gráficos gerados (PNG, DPI 300)
│   │   ├── boxplot_call2go_views.png
│   │   ├── confusion_matrix_combined.png
│   │   ├── confusion_matrix_video_only.png
│   │   ├── scatter_cross_platform.png
│   │   └── validation_metrics_per_class.png
│   ├── processed/
│   │   ├── youtube_call2go_flagged.csv  # 980 vídeos + flags Call2Go
│   │   └── call2go.db                   # Data Warehouse SQLite (ignorado por git)
│   ├── raw/
│   │   ├── spotify_metrics_2026-03-30.csv   # 50 artistas
│   │   ├── youtube_videos_raw.jsonl         # 980 vídeos brutos
│   │   └── channel_links_scraped.json       # 52 canais (50 + 2 oficiais OAC)
│   └── validation/
│       ├── adversarial_sample.csv           # NOVO: 91 vídeos, 9 estratos (Fase 7)
│       ├── blind_annotation.csv             # CSV cego v2: +channel_url +channel_bio com links (Fase 7)
│       ├── blind_annotation.xlsx            # NOVO: Excel formatado para anotação humana (Fase 7)
│       ├── ground_truth_prefilled.csv       # Pré-anotação automática (CIRCULAR - evidência de auditoria)
│       ├── ground_truth.csv                 # SERÁ SOBRESCRITO com anotação cega
│       ├── manual_sample.csv               # Amostra original (50 vídeos, seed=42)
│       ├── cross_validation_report.csv      # Resultado humano vs. máquina (com Kappa + IC)
│       ├── cross_validation_report_metrics.json  # Métricas JSON
│       ├── artist_cross_platform_profile.csv     # Perfil 49 artistas (YouTube + Spotify)
│       ├── cross_platform_report.txt             # Relatório bidirecional
│       ├── direction_a_youtube_to_spotify.png    # Scatter Direction A
│       ├── direction_b_spotify_to_youtube.png    # Scatter Direction B
│       └── bidirectional_correlation_matrix.png  # Heatmap correlações
├── tests/
│   ├── __init__.py
│   └── test_call2go_detector.py  # 77 testes adversariais, 11 grupos
├── notebooks/                    # Reservado para Jupyter notebooks
├── src/
│   ├── __init__.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── artist_source_builder.py  # Fonte oficial: playlists Spotify
│   │   ├── channel_link_scraper.py   # Web scraper: aba Sobre do YouTube
│   │   ├── spotify_collector.py      # Coleta Spotify API
│   │   └── youtube_collector.py      # Coleta YouTube API
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── eda_analysis.py           # Análise exploratória
│   │   ├── hypothesis_testing.py     # Teste Mann-Whitney U
│   │   └── spotify_impact_analysis.py  # Análise cross-platform
│   ├── db/
│   │   ├── __init__.py
│   │   └── db_builder.py             # Construtor do Data Warehouse SQLite
│   ├── processors/
│   │   ├── __init__.py
│   │   └── call2go_detector.py       # Motor regex (77 testes passam)
│   └── validation/
│       ├── __init__.py
│       ├── sample_generator.py       # Amostra aleatória (50 vídeos)
│       ├── adversarial_sampler.py    # NOVO: Amostra estratificada (91 vídeos, 9 estratos)
│       ├── blind_annotator.py        # CSV cego v2: +channel_url +channel_bio com links
│       ├── excel_formatter.py        # NOVO: Gera Excel formatado (.xlsx) para anotacao
│       ├── ground_truth_helper.py    # Pré-preenche ground truth (semi-automático)
│       ├── cross_validator.py        # Humano vs. máquina + Cohen's Kappa + Bootstrap IC 95%
│       ├── cross_platform_validator.py  # Análise bidirecional YouTube <-> Spotify
│       └── agreement_report.py       # Matrizes de confusão + métricas visuais + Kappa
├── artigo_latex/                     # Artigo SBC (NÃO MEXER até autorização)
│   ├── main.tex
│   ├── references.bib
│   ├── sbc-template.sty
│   ├── sbc.bst
│   └── figs/                         # Figuras para o artigo (cópias de data/plots + validation)
├── SBC_Conferences_Template_.../     # Template referência (.gitignore exclui)
└── memory-bank/                      # Contexto persistente do projeto
```

## Web Scraping (Links Estruturados)
- **`channel_link_scraper.py`** — scraper 2-fases para links da aba Sobre
  - Fase 1: Página principal do canal → `ytInitialData`
  - Fase 2: Página `/about` → `channelExternalLinkViewModel`
  - **Descoberta de canal oficial**: para canais OAC, busca via YouTube Search
    `{artist_name} canal oficial` com filtro `sp=EgIQAg==` (tipo: Canal)
    Testa até 5 resultados, retorna o primeiro não-OAC
  - Fix crítico: `\u0026` → `&` no JSON para decodificar redirect URLs completas
  - Detecta canais OAC via "Gerado automaticamente pelo YouTube"
  - Cache: `data/raw/channel_links_scraped.json` (52 canais: 50 primários + 2 oficiais)
  - 29/50 artistas com Spotify no About, 2/50 canais OAC
  - Rate limiting: 2s entre requests, 0.5s entre fases do mesmo canal

## Dados de Qualidade (07/04/2026 — Pós-Auditoria Fase 7)
| Métrica | Valor |
|---------|-------|
| Total de artistas | 49 (Top 50 BR, MJ Records removido) |
| Total de vídeos | 980 (20 mais visualizados/artista) |
| Vídeos auto-gerados | 40 (4.1%) |
| Canais OAC | 2/52 (3.8%) |
| Artistas com Spotify no About | 29/52 (55.8%) |
| Vídeos com link_direto | 575 (58.7%) |
| Vídeos com texto_implicito | 0 (0%) |
| Vídeos sem Call2Go (nenhum) | 405 (41.3%) |
| Call2Go via canal (fonte) | 494 (50.4%) |
| Call2Go via ambos (fonte) | 66 (6.7%) |
| Call2Go via vídeo (fonte) | 15 (1.5%) |
| Vídeos orgânicos | 940 (95.9%) |
| Testes unitários | 77 (100% passam) |
| Amostra adversarial | 91 vídeos, 9 estratos |
| Pipeline encoding | cp1252-safe (sem emojis) |

## Limitações Técnicas Conhecidas
- YouTube API tem quota diária limitada (10.000 unidades/dia, reset meia-noite Pacific)
- Spotify Popularity Score é opaco — não se sabe exatamente como é calculado
- Coleta do Spotify é snapshot pontual (30/03/2026), não série temporal contínua
- YouTube API NÃO expõe links estruturados da aba Sobre → necessário web scraping
- Spotify API NÃO expõe links externos do perfil do artista → impossível coletar links Spotify→YouTube programaticamente
- Canais OAC (auto-gerados pelo YouTube) não têm links personalizados nem descrição
- Web scraping depende da estrutura HTML do YouTube (pode quebrar com atualizações)
- Direção B da validação bidirecional é correlação, não causalidade (possível variável confundidora: fama geral)
