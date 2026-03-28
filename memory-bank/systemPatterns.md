# System Patterns — TCC Call2Go

## Arquitetura Geral
```
Coleta (APIs) → Processamento (NLP/Regex) → Armazenamento (SQLite) → Análise (Estatística + Visualização)
```

## Padrão ETL
| Etapa | Script | Input | Output |
|-------|--------|-------|--------|
| Extract | `src/collectors/spotify_collector.py` | Spotify API | `data/raw/spotify_metrics_YYYY-MM-DD.csv` |
| Extract | `src/collectors/youtube_collector.py` | YouTube Data API v3 | `data/raw/youtube_videos_raw.jsonl` |
| Transform | `src/processors/call2go_detector.py` | JSONL bruto | `data/processed/youtube_call2go_flagged.csv` |
| Load | `src/db/db_builder.py` | CSVs processados | `data/processed/call2go.db` (SQLite) |
| Analyze | `src/analytics/eda_analysis.py` | SQLite DB | Gráficos PNG + stats no console |
| Analyze | `src/analytics/hypothesis_testing.py` | SQLite DB | Resultado do teste Mann-Whitney U |
| Analyze | `src/analytics/spotify_impact_analysis.py` | SQLite DB | Gráfico scatter + teste cross-platform |

## Schema do Data Warehouse (SQLite)
```
dim_artist (artist_name PK, spotify_id, youtube_channel_id)
    │
    ├──< fact_yt_videos (video_id, artist_name FK, title, published_at,
    │                     view_count, like_count, comment_count,
    │                     has_call2go, call2go_type)
    │
    └──< fact_spotify_metrics (date, spotify_id FK, artist_name,
                                followers, popularity)
```

## Padrões de Código
- **Linguagem:** Python 3 com código em inglês, comentários em português
- **Dados brutos:** JSONL para YouTube (streaming-friendly), CSV para Spotify
- **Autenticação:** Variáveis de ambiente via `.env` + `python-dotenv`
- **Cada script é executável standalone** (`if __name__ == "__main__"`)
- **Sem classes** — funções procedurais simples, adequado para pipeline acadêmico
- **Pandas** como abstração central de dados em todo o pipeline

## Convenções de Nomes
- Dados de referência (seed): `data/seed/`
- Arquivos de dados brutos: `data/raw/`
- Arquivos processados: `data/processed/`
- Gráficos para o TCC: `data/plots/`
- Prefixo de data nos CSVs do Spotify: `spotify_metrics_YYYY-MM-DD.csv`

## Padrões de Detecção NLP (Regex)
```python
# Link direto
r'(https?://(?:open\.spotify\.com|spoti\.fi)[^\s]+)'

# Texto implícito (5 padrões, em ordem de especificidade)
r'ou[çc]a no spotify'
r'dispon[ií]vel no spotify'
r'stream.*spotify'
r'ouvir.*spotify'
r'\bspotify\b'  # fallback genérico
```
