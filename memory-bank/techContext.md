# Tech Context — TCC Call2Go

## Stack Principal
| Tecnologia | Versão/Info | Uso |
|------------|-------------|-----|
| Python | 3.12.9 | Linguagem principal |
| Pandas | latest | Manipulação de dados |
| Spotipy | 2.23.0 | Wrapper da Spotify Web API |
| google-api-python-client | 2.97.0 | YouTube Data API v3 |
| Requests | 2.31.0 | HTTP requests |
| python-dotenv | 1.0.0 | Gerenciamento de env vars |
| SQLite3 | built-in | Data Warehouse local |
| Matplotlib | latest | Visualização |
| Seaborn | latest | Visualização estatística |
| SciPy | latest | Testes estatísticos |

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
├── requirements.txt
├── data/
│   ├── seed/
│   │   └── artistas.csv              # Dimensão: 49 artistas (MJ Records removido)
│   ├── plots/                        # Gráficos gerados (PNG, DPI 300)
│   ├── processed/
│   │   ├── youtube_call2go_flagged.csv  # YouTube + flags Call2Go (980 vídeos)
│   │   └── call2go.db                   # Data Warehouse SQLite
│   ├── raw/
│   │   ├── spotify_metrics_2026-03-30.csv   # Snapshot Spotify (50 artistas)
│   │   ├── youtube_videos_raw.jsonl         # 980 vídeos brutos (MJ Records removido)
│   │   └── channel_links_scraped.json       # 52 canais (50 + 2 oficiais)
│   └── validation/                      # Artefatos de validação
│       ├── manual_sample.csv            # Amostra para anotação (50 vídeos, seed=42)
│       ├── ground_truth_prefilled.csv   # Pré-anotação automática (para revisão)
│       ├── ground_truth.csv             # Anotação humana final (preenchido pelo aluno)
│       ├── cross_validation_report.csv  # Resultado humano vs. máquina
│       ├── cross_validation_report_metrics.json  # Métricas de concordância
│       ├── artist_cross_platform_profile.csv     # Perfil 50 artistas (YouTube + Spotify)
│       ├── cross_platform_report.txt             # Relatório bidirecional detalhado
│       ├── direction_a_youtube_to_spotify.png    # Scatter Direction A
│       ├── direction_b_spotify_to_youtube.png    # Scatter Direction B
│       └── bidirectional_correlation_matrix.png  # Heatmap correlações
├── notebooks/                        # Reservado para Jupyter notebooks
├── src/
│   ├── __init__.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── artist_source_builder.py  # Fonte oficial de artistas (playlists Spotify)
│   │   ├── channel_link_scraper.py   # Web scraper: links da aba Sobre do YouTube
│   │   ├── spotify_collector.py      # Coleta Spotify
│   │   └── youtube_collector.py      # Coleta YouTube
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── eda_analysis.py           # Análise exploratória
│   │   ├── hypothesis_testing.py     # Teste Mann-Whitney U
│   │   └── spotify_impact_analysis.py  # Análise cross-platform
│   ├── db/
│   │   ├── __init__.py
│   │   └── db_builder.py             # Construtor do Data Warehouse
│   ├── processors/
│   │   ├── __init__.py
│   │   └── call2go_detector.py       # Motor regex (classificador)
│   └── validation/                   # ** ARTEFATO CENTRAL DO TCC **
│       ├── __init__.py
│       ├── sample_generator.py       # Gera amostra para anotação manual
│       ├── ground_truth_helper.py    # Pré-preenche ground truth (semi-automático)
│       ├── cross_validator.py        # A "volta": humano vs. máquina (2 níveis)
│       ├── cross_platform_validator.py  # Análise bidirecional YouTube ↔ Spotify
│       └── agreement_report.py       # Matriz de confusão e métricas visuais
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

## Dados de Qualidade (31/03/2026)
| Métrica | Valor |
|---------|-------|
| Total de artistas | 50 (Top 50 BR) |
| Total de vídeos | 1.000 (20 mais visualizados/artista) |
| Vídeos auto-gerados | 40 (4%) |
| Canais OAC | 2/50 (4%) |
| Artistas com Spotify no About | 29/50 (58%) |
| Vídeos com link_direto | 528 (52.8%) |
| Vídeos com texto_implicito | 48 (4.8%) |
| Vídeos sem Call2Go (nenhum) | 424 (42.4%) |
| Call2Go via canal (fonte) | 475 |
| Call2Go via vídeo (fonte) | 101 |
| Vídeos orgânicos | 960 (96%) |

## Limitações Técnicas Conhecidas
- YouTube API tem quota diária limitada (10.000 unidades/dia, reset meia-noite Pacific)
- Spotify Popularity Score é opaco — não se sabe exatamente como é calculado
- Coleta do Spotify é snapshot pontual (30/03/2026), não série temporal contínua
- YouTube API NÃO expõe links estruturados da aba Sobre → necessário web scraping
- Spotify API NÃO expõe links externos do perfil do artista → impossível coletar links Spotify→YouTube programaticamente
- Canais OAC (auto-gerados pelo YouTube) não têm links personalizados nem descrição
- Web scraping depende da estrutura HTML do YouTube (pode quebrar com atualizações)
- Direção B da validação bidirecional é correlação, não causalidade (possível variável confundidora: fama geral)
