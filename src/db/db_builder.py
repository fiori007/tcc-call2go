import sqlite3
import pandas as pd
import glob
import os


def build_database():
    # ADR: Estratégia batch/rebuild (26/04/2026)
    # Decisao: DROP + recreate completo a cada execucao (nao incremental).
    # Justificativa:
    #   - Reprodutibilidade analitica > eficiencia de escrita.
    #   - SQLite e artefato de pesquisa (nao producao); rebuild < 1s.
    #   - Sem concorrencia de escrita (pipeline sequencial, single-process).
    #   - Incremental exige merge de schema e deteccao de conflitos sem ganho.
    # Serie temporal (Spotify, Last.fm):
    #   - Concatena todos os snapshots via glob("data/raw/*_metrics_*.csv").
    #   - Dedup por (date, artist_id/artist_name) preserva evolucao de metricas
    #     ao longo das coletas sem duplicar linhas do mesmo dia.
    print("Iniciando a construção do Banco de Dados Relacional (SQLite)...")

    # Define o caminho do banco de dados
    os.makedirs("data/processed", exist_ok=True)
    db_path = "data/processed/call2go.db"

    # Remove banco anterior para rebuild limpo
    if os.path.exists(db_path):
        os.remove(db_path)

    # Conecta ao banco (cria o arquivo se não existir)
    conn = sqlite3.connect(db_path)

    # ---------------------------------------------------------
    # 1. Carga da Dimensão Artista (Nossa base fixa)
    # ---------------------------------------------------------
    print("Carregando tabela dim_artist...")
    df_artists = pd.read_csv("data/seed/artistas.csv")
    df_artists.to_sql('dim_artist', conn, if_exists='replace', index=False)

    # ---------------------------------------------------------
    # 2. Carga dos Fatos do YouTube (Vídeos e NLP)
    # ---------------------------------------------------------
    yt_file = "data/processed/youtube_call2go_flagged.csv"
    if os.path.exists(yt_file):
        print("Carregando tabela fact_yt_videos...")
        df_yt = pd.read_csv(yt_file)

        # Converte a data de publicação para o formato datetime do Pandas para garantir consistência
        df_yt['published_at'] = pd.to_datetime(
            df_yt['published_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

        df_yt.to_sql('fact_yt_videos', conn, if_exists='replace', index=False)
    else:
        print(f"[ERRO] Arquivo {yt_file} não encontrado. Pare a execução.")

    # ---------------------------------------------------------
    # 3. Carga dos Fatos do Spotify (Série Temporal)
    # ---------------------------------------------------------
    print("Carregando tabela fact_spotify_metrics...")
    # Usa glob para pegar todos os arquivos diários gerados pelo coletor do Spotify
    spotify_files = glob.glob("data/raw/spotify_metrics_*.csv")

    if spotify_files:
        df_spotify_list = [pd.read_csv(f) for f in spotify_files]
        df_spotify = pd.concat(df_spotify_list, ignore_index=True)

        # Remove duplicatas (caso o coletor tenha rodado duas vezes no mesmo dia para o mesmo artista)
        df_spotify.drop_duplicates(subset=['date', 'spotify_id'], inplace=True)

        df_spotify.to_sql('fact_spotify_metrics', conn,
                          if_exists='replace', index=False)
    else:
        print("[ERRO] Nenhum arquivo de métricas do Spotify encontrado.")

    # ---------------------------------------------------------
    # 4. Carga dos Fatos do Last.fm (metricas por artista)
    # ---------------------------------------------------------
    print("Carregando tabela fact_lastfm_metrics...")
    lastfm_files = glob.glob("data/raw/lastfm_artists_*.csv")

    if lastfm_files:
        df_lastfm_list = [pd.read_csv(f) for f in lastfm_files]
        df_lastfm = pd.concat(df_lastfm_list, ignore_index=True)

        # Remove duplicatas (mesmo artista no mesmo dia)
        df_lastfm.drop_duplicates(
            subset=['date', 'artist_name'], inplace=True)

        df_lastfm.to_sql('fact_lastfm_metrics', conn,
                         if_exists='replace', index=False)
    else:
        print("[AVISO] Nenhum arquivo de métricas do Last.fm encontrado.")

    # ---------------------------------------------------------
    # 5. Carga dos Charts Last.fm Brasil (artistas + tracks)
    # ---------------------------------------------------------
    print("Carregando tabela fact_lastfm_chart_artists...")
    chart_artist_files = glob.glob(
        "data/raw/lastfm_chart_artists_brazil_*.csv")
    if chart_artist_files:
        df_ca_list = [pd.read_csv(f) for f in chart_artist_files]
        df_ca = pd.concat(df_ca_list, ignore_index=True)
        df_ca.drop_duplicates(subset=['date', 'artist_name'], inplace=True)
        df_ca.to_sql('fact_lastfm_chart_artists', conn,
                     if_exists='replace', index=False)
    else:
        print("[AVISO] Nenhum arquivo de chart artistas Last.fm encontrado.")

    print("Carregando tabela fact_lastfm_chart_tracks...")
    chart_track_files = glob.glob(
        "data/raw/lastfm_chart_tracks_brazil_*.csv")
    if chart_track_files:
        df_ct_list = [pd.read_csv(f) for f in chart_track_files]
        df_ct = pd.concat(df_ct_list, ignore_index=True)
        df_ct.drop_duplicates(
            subset=['date', 'artist_name', 'track_name'], inplace=True)
        df_ct.to_sql('fact_lastfm_chart_tracks', conn,
                     if_exists='replace', index=False)
    else:
        print("[AVISO] Nenhum arquivo de chart tracks Last.fm encontrado.")

    # Fecha a conexão para salvar no disco
    conn.close()

    print(
        f"\n[OK] Banco de dados construído e populado com sucesso em: {db_path}")
    print("[OK] Tabelas disponíveis: dim_artist, fact_yt_videos, "
          "fact_spotify_metrics, fact_lastfm_metrics, "
          "fact_lastfm_chart_artists, fact_lastfm_chart_tracks")


if __name__ == "__main__":
    build_database()
