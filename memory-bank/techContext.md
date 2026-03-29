# Tech Context — TCC Call2Go

## Stack Principal
| Tecnologia | Versão/Info | Uso |
|------------|-------------|-----|
| Python | 3.x | Linguagem principal |
| Pandas | latest | Manipulação de dados |
| Spotipy | 2.23.0 | Wrapper da Spotify Web API |
| google-api-python-client | 2.97.0 | YouTube Data API v3 |
| Requests | 2.31.0 | HTTP requests |
| python-dotenv | 1.0.0 | Gerenciamento de env vars |
| SQLite3 | built-in | Data Warehouse local |
| Matplotlib | (comentado no requirements) | Visualização |
| Seaborn | (comentado no requirements) | Visualização estatística |
| SciPy | (comentado no requirements) | Testes estatísticos |

## APIs Externas
- **Spotify Web API** — via OAuth2 Client Credentials (sem login do usuário)
  - Endpoint: artist metadata (followers, popularity)
  - Autenticação: `SPOTIFY_CLIENT_ID` + `SPOTIFY_CLIENT_SECRET`
- **YouTube Data API v3** — via API Key
  - Endpoints: search, channels, playlistItems, videos
  - Autenticação: `YOUTUBE_API_KEY`
  - Resolução dinâmica de canal pelo nome do artista

## Configuração Necessária
Arquivo `.env` na raiz do projeto com:
```
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
YOUTUBE_API_KEY=...
```

## Dependências Não Listadas no requirements.txt
As bibliotecas de análise estão comentadas no `requirements.txt` mas são usadas nos scripts:
- `matplotlib` — usado em `eda_analysis.py` e `spotify_impact_analysis.py`
- `seaborn` — usado em `eda_analysis.py` e `spotify_impact_analysis.py`
- `scipy` — usado em `hypothesis_testing.py` e `spotify_impact_analysis.py`

## Estrutura de Diretórios
```
tcc_call2go/
├── requirements.txt
├── data/
│   ├── seed/
│   │   └── artistas.csv              # Dimensão: lista mestre (fonte oficial)
│   ├── plots/                        # Gráficos gerados (PNG, DPI 300)
│   ├── processed/
│   │   ├── youtube_call2go_flagged.csv  # YouTube + flags Call2Go
│   │   └── call2go.db                   # Data Warehouse SQLite
│   ├── raw/
│   │   ├── spotify_metrics_*.csv        # Série temporal Spotify
│   │   └── youtube_videos_raw.jsonl     # Dados brutos YouTube
│   └── validation/                      # Artefatos de validação
│       ├── manual_sample.csv            # Amostra para anotação manual
│       ├── ground_truth.csv             # Anotação humana (preenchido manualmente)
│       ├── cross_validation_report.csv  # Resultado humano vs. máquina
│       └── cross_validation_report_metrics.json  # Métricas de concordância
├── notebooks/                        # Reservado para Jupyter notebooks
├── src/
│   ├── __init__.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── artist_source_builder.py  # Fonte oficial de artistas (playlists Spotify)
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
│       ├── cross_validator.py        # A "volta": humano vs. máquina (3 níveis)
│       └── agreement_report.py       # Matriz de confusão e métricas visuais
└── memory-bank/                      # Contexto persistente do projeto
```

## Limitações Técnicas Conhecidas
- YouTube API tem quota diária limitada (10.000 unidades/dia)
- Resolução de canal por nome (`search().list`) consome 100 unidades por chamada
- Spotify Popularity Score é opaco — não se sabe exatamente como é calculado
- Coleta do Spotify é snapshot pontual, não série temporal contínua
