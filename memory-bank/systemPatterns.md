# System Patterns — TCC Call2Go

## Arquitetura Geral
```
Fonte Oficial → Coleta (APIs) → Processamento (Regex) → VALIDAÇÃO → Armazenamento (SQLite) → Análise
                                                          ├─ Humano vs. Máquina (cross_validator)
                                                          └─ YouTube ↔ Spotify (cross_platform_validator)
```

## Padrão ETL + Validação
| Etapa | Script | Input | Output |
|-------|--------|-------|--------|
| **Seed** | `src/collectors/artist_source_builder.py` | Playlists Oficiais Spotify | `data/seed/artistas.csv` |
| Extract | `src/collectors/spotify_collector.py` | Spotify API | `data/raw/spotify_metrics_YYYY-MM-DD.csv` |
| Extract | `src/collectors/youtube_collector.py` | YouTube Data API v3 | `data/raw/youtube_videos_raw.jsonl` |
| Transform | `src/processors/call2go_detector.py` | JSONL bruto | `data/processed/youtube_call2go_flagged.csv` |
| **Validate** | `src/validation/sample_generator.py` | JSONL bruto | `data/validation/manual_sample.csv` |
| **Validate** | `src/validation/cross_validator.py` | Ground truth + JSONL | `data/validation/cross_validation_report.csv` |
| **Validate** | `src/validation/agreement_report.py` | Report CSV + métricas | Gráficos de concordância |
| **Validate** | `src/validation/cross_platform_validator.py` | Flagged CSV + Spotify CSV | Relatório bidirecional + gráficos |
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
