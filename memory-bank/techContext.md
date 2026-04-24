# Tech Context -- TCC Call2Go

## Stack
| Tecnologia | Versao | Uso |
|------------|--------|-----|
| Python | 3.12.9 | Linguagem principal |
| Pandas | 3.0.1 | Manipulacao de dados |
| Spotipy | 2.23.0 | Spotify Web API |
| google-api-python-client | 2.97.0 | YouTube Data API v3 |
| openpyxl | 3.1.5 | Excel formatado |
| scikit-learn | 1.8.0 | Cohen's Kappa |
| SciPy | 1.17.1 | Testes estatisticos |
| Matplotlib + Seaborn | 3.10.8 / 0.13.2 | Graficos |
| pytest | 9.0.3 | Testes unitarios |
| Playwright | 1.52.0 | Auditoria automatizada de links de perfil |

## APIs
- **Spotify:** OAuth2 Client Credentials (SPOTIFY_CLIENT_ID + SECRET)
- **YouTube:** API Key (YOUTUBE_API_KEY), quota 10k/dia
  - Otimizacao: playlistItems.list (1 unit) vs search.list (100 units)
  - Resume: le JSONL existente, pula artistas ja coletados
- **Last.fm:** API Key (LASTFM_API_KEY), sem OAuth para leitura
  - Endpoints: artist.getInfo, artist.getTopTracks, artist.getTopAlbums
  - Charts BR: geo.getTopArtists, geo.getTopTracks (country="Brazil")
  - Rate limit: 0.25s entre requests, autocorrect=1 para nomes

## Estrutura de Arquivos
`
tcc_call2go/
  run_pipeline.py            # Orquestrador 14 etapas
  requirements.txt           # Dependencias pinadas
  src/
    collectors/              # Coleta de dados (APIs + scraping)
    processors/              # Deteccao Call2Go + processamento de charts
    db/                      # Data Warehouse SQLite
    analytics/               # EDA, hipoteses, cross-platform
    validation/              # Anotacao, cross-validation, agreement
  data/
    seed/                    # artistas.csv (67 artistas)
    raw/                     # JSONL, CSVs brutos, scraped JSON
    processed/               # Flagged CSV, SQLite DB
    plots/                   # Graficos PNG (DPI 300)
    validation/              # Census Excel, plots bidirecional
  tests/                     # 77 testes adversariais
  artigo_latex/              # TCC em LaTeX (SBC format)
  memory-bank/               # Contexto persistente
`

## Limitacoes
- YouTube API: 10k units/dia, reset meia-noite Pacific (04:00 BRT)
- Spotify Popularity Score: opaco, snapshot pontual
- YouTube API nao expoe links da aba Sobre -> web scraping necessario
- Spotify API nao expoe links externos do perfil
- Scraping de perfis depende de disponibilidade de pagina (cache-first reduz variacao entre reruns)
