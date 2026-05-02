"""Construcao do Data Warehouse SQLite (batch/rebuild).

ADR (26/04/2026): Estrategia DROP + recreate completo a cada execucao
(nao incremental). Justificativas:
- Reprodutibilidade analitica > eficiencia de escrita.
- SQLite e artefato de pesquisa (nao producao); rebuild < 1s.
- Sem concorrencia de escrita (pipeline sequencial, single-process).
- Incremental exigiria merge de schema e deteccao de conflitos sem ganho.

Serie temporal (Spotify, Last.fm):
- Concatena todos os snapshots via glob('data/raw/*_metrics_*.csv').
- Dedup por (date, artist_id/artist_name) preserva evolucao de metricas
  ao longo das coletas sem duplicar linhas do mesmo dia.
"""

import sqlite3
import pandas as pd
import glob
import os


# Indices a criar apos popular cada tabela. (tabela, nome_indice, colunas)
# Acelera joins/lookups no SQL ad-hoc sem custo significativo no rebuild.
_INDEX_SPECS = [
    ('dim_artist',                'idx_dim_artist_name',     '(artist_name)'),
    ('fact_yt_videos',            'idx_yt_artist',           '(artist_name)'),
    ('fact_yt_videos',            'idx_yt_video',            '(video_id)'),
    ('fact_spotify_metrics',      'idx_sp_date_id',          '(date, spotify_id)'),
    ('fact_lastfm_metrics',       'idx_lfm_date_artist',     '(date, artist_name)'),
    ('fact_lastfm_chart_artists', 'idx_lfm_chart_a',         '(date, artist_name)'),
    ('fact_lastfm_chart_tracks',  'idx_lfm_chart_t',         '(date, artist_name, track_name)'),
]


def _load_concat_dedup(pattern, dedup_subset, label):
    """Carrega N CSVs por glob, concatena e deduplica. Retorna df ou None."""
    files = glob.glob(pattern)
    if not files:
        print(f"[AVISO] Nenhum arquivo encontrado para {label}: {pattern}")
        return None
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df.drop_duplicates(subset=dedup_subset, inplace=True)
    return df


def _create_indices(conn):
    """Cria indices em FKs/colunas chave para acelerar consultas."""
    cursor = conn.cursor()
    for table, idx_name, cols in _INDEX_SPECS:
        # Confirma que a tabela existe antes de tentar indexar
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if cursor.fetchone() is None:
            continue
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} {cols}")
    conn.commit()


def build_database():
    print("Iniciando a construcao do Banco de Dados Relacional (SQLite)...")

    os.makedirs("data/processed", exist_ok=True)
    db_path = "data/processed/call2go.db"

    if os.path.exists(db_path):
        os.remove(db_path)

    # Context manager garante close mesmo se to_sql falhar a meio caminho
    with sqlite3.connect(db_path) as conn:
        # 1. Dimensao artista
        print("Carregando tabela dim_artist...")
        df_artists = pd.read_csv("data/seed/artistas.csv")
        df_artists.to_sql('dim_artist', conn, if_exists='replace', index=False)

        # 2. Fatos YouTube (videos com flags Call2Go)
        yt_file = "data/processed/youtube_call2go_flagged.csv"
        if os.path.exists(yt_file):
            print("Carregando tabela fact_yt_videos...")
            df_yt = pd.read_csv(yt_file)
            df_yt['published_at'] = pd.to_datetime(
                df_yt['published_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df_yt.to_sql('fact_yt_videos', conn, if_exists='replace', index=False)
        else:
            print(f"[ERRO] Arquivo {yt_file} nao encontrado.")

        # 3. Fatos Spotify (serie temporal)
        print("Carregando tabela fact_spotify_metrics...")
        df_sp = _load_concat_dedup(
            "data/raw/spotify_metrics_*.csv", ['date', 'spotify_id'], "Spotify metrics")
        if df_sp is not None:
            df_sp.to_sql('fact_spotify_metrics', conn, if_exists='replace', index=False)

        # 4. Fatos Last.fm (artistas)
        print("Carregando tabela fact_lastfm_metrics...")
        df_lfm = _load_concat_dedup(
            "data/raw/lastfm_artists_*.csv", ['date', 'artist_name'], "Last.fm artists")
        if df_lfm is not None:
            df_lfm.to_sql('fact_lastfm_metrics', conn, if_exists='replace', index=False)

        # 5. Charts Last.fm Brasil (artistas)
        print("Carregando tabela fact_lastfm_chart_artists...")
        df_ca = _load_concat_dedup(
            "data/raw/lastfm_chart_artists_brazil_*.csv",
            ['date', 'artist_name'], "Last.fm chart artists")
        if df_ca is not None:
            df_ca.to_sql('fact_lastfm_chart_artists', conn, if_exists='replace', index=False)

        # 6. Charts Last.fm Brasil (tracks)
        print("Carregando tabela fact_lastfm_chart_tracks...")
        df_ct = _load_concat_dedup(
            "data/raw/lastfm_chart_tracks_brazil_*.csv",
            ['date', 'artist_name', 'track_name'], "Last.fm chart tracks")
        if df_ct is not None:
            df_ct.to_sql('fact_lastfm_chart_tracks', conn, if_exists='replace', index=False)

        # Cria indices apos popular tudo
        print("Criando indices...")
        _create_indices(conn)

    print(f"\n[OK] Banco de dados construido em: {db_path}")
    print("[OK] Tabelas: dim_artist, fact_yt_videos, fact_spotify_metrics, "
          "fact_lastfm_metrics, fact_lastfm_chart_artists, fact_lastfm_chart_tracks")


if __name__ == "__main__":
    build_database()
