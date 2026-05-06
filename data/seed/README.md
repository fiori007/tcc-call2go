# data/seed/ — Histórico técnico, NÃO universo de análise

> **Atenção:** os arquivos deste diretório são **histórico técnico**.
> Nenhum deles representa o universo de análise atual do TCC.

## O que são esses arquivos

### `legacy_v1_artistas.csv`

Lista de **67 artistas brasileiros** identificada na **versão 1** da
metodologia (interseção persistente entre Spotify Top 200 BR e YouTube Top
100 BR no Q1 2026).

A v1 foi **abandonada** na Fase 18 (02/05/2026) porque introduzia
viés de seleção: artistas que dominavam apenas uma plataforma ficavam
de fora, mesmo sendo relevantes no mercado.

### Por que esse arquivo ainda existe?

Porque a coleta original de vídeos do YouTube (~2.214 vídeos hoje) foi feita
com base nesses 67 artistas. Os módulos de coleta (`youtube_collector.py`,
`spotify_collector.py`, `lastfm_collector.py`, `channel_link_scraper.py`)
ainda referenciam esse arquivo apenas como **lista de canais a coletar
métricas** — não como universo analítico.

### Onde está o universo de análise atual?

O universo é definido pelo **Top-K do Rank Fusion**:

```
data/processed/ranking_fusion_scores.csv
```

A coluna `in_top_k=True` marca os artistas que entram nas análises
estatísticas. Atualmente: **46 artistas (Top-20% de 228 primários
cross-platform)**.

Após a Fase 19 (06/05/2026), todos os 46 artistas Top-K têm cobertura
completa de vídeos Call2Go (incluindo BTS, Anitta, Bad Bunny, Murilo Huff
e outros que não estavam na v1). O arquivo `legacy_v1_artistas.csv` é uma
referência histórica de onde a coleta começou.

## Não use este arquivo como filtro analítico

Se você for adicionar uma nova análise ao projeto, **NÃO** comece com:

```python
# ERRADO — usa universo legado v1
df_seed = pd.read_csv('data/seed/legacy_v1_artistas.csv')
```

Use o helper compartilhado:

```python
# CERTO — usa universo Top-K do Rank Fusion (Fase 19)
from src.analytics._universe import filter_videos_to_topk
df_topk = filter_videos_to_topk(df_videos, artist_col='artist_name')
```

ou:

```python
from src.analytics._universe import load_topk_dataframe
df = load_topk_dataframe()  # 46 artistas, todas as colunas do Rank Fusion
```
