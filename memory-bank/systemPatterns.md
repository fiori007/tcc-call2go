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
| **Seed** | `src/collectors/artist_source_builder.py` | Playlists Spotify (fallback dinâmico) | `data/seed/artistas.csv` |
| Extract | `src/collectors/spotify_collector.py` | Spotify API | `data/raw/spotify_metrics_YYYY-MM-DD.csv` |
| Extract | `src/collectors/youtube_collector.py` | YouTube Data API v3 | `data/raw/youtube_videos_raw.jsonl` |
| Extract | `src/collectors/channel_link_scraper.py` | Web scraping aba Sobre | `data/raw/channel_links_scraped.json` |
| Transform | `src/processors/call2go_detector.py` | JSONL + scraped JSON + seed | `data/processed/youtube_call2go_flagged.csv` |
| **Validate** | `src/validation/sample_generator.py` | JSONL bruto | `data/validation/manual_sample.csv` |
| **Validate** | ~~`src/validation/ground_truth_helper.py`~~ | ~~Sample + JSONL~~ | ~~`ground_truth_prefilled.csv`~~ **[DEPRECATED -- validação circular]** |
| **Validate** | `src/validation/adversarial_sampler.py` | JSONL bruto | Amostra estratificada (91 vídeos, 9 estratos) |
| **Validate** | `src/validation/blind_annotator.py` | JSONL + scraped JSON + seed | `blind_annotation_census.csv` (censo 920 vídeos, cego) |
| **Validate** | `src/validation/blind_annotator.py --detector-answers` | JSONL + scraped JSON + seed | `detector_answers_census.csv` (respostas do detector) |
| **Validate** | `src/validation/excel_formatter.py` | CSVs de anotação | `.xlsx` formatado (dropdowns SIM/NÃO, README) |
| **Validate** | `src/validation/cross_validator.py` | Ground truth + JSONL + seed | `cross_validation_report.csv` (Kappa + Bootstrap CI, 3 níveis) |
| **Validate** | `src/validation/agreement_report.py` | Report CSV + métricas | 3 matrizes de confusão (vídeo/canal/combinado) + P/R/F1 |
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
# Link direto (3 domínios oficiais do Spotify)
r'(https?://(?:open\.spotify\.com|spoti\.fi|sptfy\.com)[^\s]+)'

# Texto implícito (4 padrões CTA, sem fallback genérico)
r'ou[çc]a no spotify'
r'dispon[ií]vel no spotify'
r'stream.*spotify'
r'ouvir.*spotify'
# \bspotify\b REMOVIDO — causava falsos positivos com menções narrativas
```

## Filtros de Qualidade
```python
# Vídeos auto-gerados (Content ID / OAC)
def is_auto_generated(description):
    # Detecta: "Provided to YouTube by <distribuidora>"
    # 40/980 videos (4.1%) sao auto-gerados

# Menções narrativas (NÃO são Call2Go)
_NARRATIVE_PATTERNS = [
    r'chart\w*\s+(?:do|no)\s+spotify',   # "charts do Spotify"
    r'ranking\s+(?:do|no)\s+spotify',
    r'top\s+\d+\s+(?:do|no)\s+spotify',
    r'milh[ãõ]\w*\s+(?:de\s+)?(?:plays?|streams?)\s+(?:no|do)\s+spotify',
]

# Detecção em 3 níveis:
# 1. Vídeo: regex na descrição do vídeo
# 2. Canal (scraped): links estruturados da aba Sobre (web scraping)
#    Prioridade: canal oficial do seed (artistas.csv), fallback pelo channel_id do JSONL
# 3. Combinado: AND -- vídeo E canal devem ter Call2Go
```

## Testes Unitários
- **77 testes adversariais** em `tests/test_call2go_detector.py`
- 11 grupos: DirectLinks, RedirectLinks, RedirectSemLabel, TextoImplicito, Narrativas, EdgeCases, AutoGenerated, ChannelDetection, ScrapedDetection, CenariosReais, FalsosPositivosConhecidos
- Framework: pytest 9.0.3
- Cobertura: todos os padrões regex + edge cases + falsos positivos conhecidos

## Validação Estatística
- **Cohen's Kappa** para concordância humano vs. máquina (sklearn)
- **Bootstrap CI 95%** com 2000 reamostragens (seed=42)
- **Interpretação Landis & Koch** automática no relatório
- **Amostra adversarial**: 91 vídeos estratificados em 9 estratos de dificuldade (Fase 7-8)
- **Censo completo**: 920 vídeos com XLSX formatado (dropdowns SIM/NÃO) para anotação (Fase 9)
- **Lógica combinado**: AND (vídeo E canal) — tanto no detector quanto na anotação humana
