"""Helper compartilhado: define o universo analitico (Top-K do Rank Fusion).

Fase 18 (substituicao por Rank Fusion). A logica antiga de filtrar pelos
67 artistas seed (in_dataset) foi abandonada. Todos os modulos analiticos
devem consumir este helper para obter o conjunto de artistas que entram
nas analises.

Uso tipico:
    from src.analytics._universe import filter_videos_to_topk
    df_filtered = filter_videos_to_topk(df_videos)

Ou:
    from src.analytics._universe import load_topk_artists
    topk = load_topk_artists()
    df_filtered = df[df['artist_normalized'].isin(topk)]
"""

import os
import re
import unicodedata
from typing import Optional

import pandas as pd


_RANKING_FUSION_PATH = "data/processed/ranking_fusion_scores.csv"


def _normalize_name(name: str) -> str:
    """Normaliza nome de artista para matching (mesma logica de ranking_fusion).

    NFKD lowercase, remove acentos e pontuacao, colapsa espacos.
    """
    if not isinstance(name, str):
        return ""
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    norm = norm.lower()
    norm = re.sub(r"[^\w\s]", " ", norm)
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm


def load_topk_artists(path: str = _RANKING_FUSION_PATH) -> set:
    """Carrega o conjunto de artistas do Top-K (artist_normalized).

    Returns:
        set de artist_normalized strings; vazio se arquivo nao existir.
    """
    if not os.path.exists(path):
        return set()
    df = pd.read_csv(path)
    if 'in_top_k' not in df.columns:
        # Backward-compat: arquivo antigo sem in_top_k -- retorna seed (in_dataset)
        if 'in_dataset' in df.columns:
            mask = df['in_dataset'] == True
            return set(df.loc[mask, 'artist_normalized'].dropna().tolist())
        return set()
    mask = df['in_top_k'] == True
    return set(df.loc[mask, 'artist_normalized'].dropna().tolist())


def load_topk_dataframe(path: str = _RANKING_FUSION_PATH,
                        only_topk: bool = True) -> pd.DataFrame:
    """Carrega o DataFrame do Rank Fusion completo (ou apenas Top-K).

    Args:
        only_topk: se True, retorna apenas linhas com in_top_k=True.
    """
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    if only_topk and 'in_top_k' in df.columns:
        return df[df['in_top_k'] == True].copy()
    return df


def filter_videos_to_topk(df_videos: pd.DataFrame,
                          artist_col: str = 'artist_name',
                          path: str = _RANKING_FUSION_PATH) -> pd.DataFrame:
    """Filtra um DataFrame de videos para apenas artistas no Top-K.

    Args:
        df_videos: DataFrame com coluna `artist_col` (default 'artist_name')
        artist_col: nome da coluna com nome de artista (raw)
        path: caminho do CSV do ranking_fusion

    Returns:
        Subconjunto de df_videos onde artist_col matched para Top-K.
        Retorna df_videos inalterado se o ranking_fusion_scores.csv nao existir
        (compatibilidade com primeiras execucoes do pipeline).
    """
    topk = load_topk_artists(path)
    if not topk:
        return df_videos.copy()
    if artist_col not in df_videos.columns:
        return df_videos.copy()

    df = df_videos.copy()
    df['_artist_norm'] = df[artist_col].apply(_normalize_name)
    df_filtered = df[df['_artist_norm'].isin(topk)].drop(columns=['_artist_norm'])
    return df_filtered


def topk_summary() -> dict:
    """Resumo numerico do universo Top-K para impressao em logs."""
    df = load_topk_dataframe(only_topk=False)
    if df.empty:
        return {'total': 0, 'in_top_k': 0, 'in_dataset': 0}
    return {
        'total': len(df),
        'in_top_k': int((df.get('in_top_k', False) == True).sum()),
        'in_dataset': int((df.get('in_dataset', False) == True).sum()),
    }
