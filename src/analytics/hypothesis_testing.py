import sqlite3
import pandas as pd
from scipy import stats

from src.config import ALPHA_DEFAULT
from src.analytics._universe import filter_videos_to_topk, topk_summary


def run_hypothesis_test():
    print("Iniciando Teste de Hipótese Estatística (Mann-Whitney U)...")

    # Conecta ao Data Warehouse
    conn = sqlite3.connect("data/processed/call2go.db")
    query = ("SELECT artist_name, view_count, has_call2go_or, has_call2go "
             "FROM fact_yt_videos")
    df_all = pd.read_sql_query(query, conn)
    conn.close()

    # Fase 18: restringe ao universo Top-K do Rank Fusion (substitui seed antigo)
    summary = topk_summary()
    print(f"  Universo Rank Fusion: {summary['total']} artistas total | "
          f"Top-K: {summary['in_top_k']}")
    df = filter_videos_to_topk(df_all, artist_col='artist_name')
    artists_in_videos = df['artist_name'].nunique()
    print(f"  Videos apos filtro Top-K: {len(df)}/{len(df_all)} "
          f"(de {artists_in_videos} artistas com dados)")

    alpha = ALPHA_DEFAULT

    # ------------------------------------------------------------------ #
    # ANÁLISE PRIMÁRIA: Lógica OR (Vídeo OU Canal com Call2Go)            #
    # Definição: has_call2go_or = 1 se video_call2go != 'nenhum' OU       #
    #                                channel_call2go != 'nenhum'          #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("ANÁLISE PRIMÁRIA — Lógica OR (H2)")
    print("=" * 60)

    group_or_no = df[df['has_call2go_or'] == 0]['view_count']
    group_or_yes = df[df['has_call2go_or'] == 1]['view_count']

    print(f"Grupo Controle  (OR=0, Sem Call2Go):  {len(group_or_no)}")
    print(f"Grupo Tratamento (OR=1, Com Call2Go): {len(group_or_yes)}")
    print(f"Mediana Controle:   {group_or_no.median():,.0f}")
    print(f"Mediana Tratamento: {group_or_yes.median():,.0f}")

    # H0: não há diferença. H1: Call2Go -> MAIS views.
    stat_or, p_or = stats.mannwhitneyu(
        group_or_yes, group_or_no, alternative='greater')

    print(f"\nEstatística U: {stat_or}")
    print(f"P-valor:        {p_or:.5f}")
    print(f"Nível Alpha:    {alpha}")

    if p_or < alpha:
        print("CONCLUSÃO (OR): Rejeitamos H0.")
        print(">> Vídeos de artistas com Call2Go (OR) geram MAIOR volume de views.")
    else:
        print("CONCLUSÃO (OR): Não rejeitamos H0.")
        print(">> Sem evidência de diferença estatística com lógica OR.")

    # ------------------------------------------------------------------ #
    # SUB-ANÁLISE: Lógica AND (Vídeo E Canal com Call2Go)                 #
    # Definição: has_call2go = 1 apenas se ambas as fontes detectaram      #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("SUB-ANÁLISE — Lógica AND (requer vídeo E canal)")
    print("=" * 60)

    group_and_no = df[df['has_call2go'] == 0]['view_count']
    group_and_yes = df[df['has_call2go'] == 1]['view_count']

    print(f"Grupo Controle  (AND=0, Sem Call2Go):  {len(group_and_no)}")
    print(f"Grupo Tratamento (AND=1, Com Call2Go): {len(group_and_yes)}")
    print(f"Mediana Controle:   {group_and_no.median():,.0f}")
    print(f"Mediana Tratamento: {group_and_yes.median():,.0f}")

    stat_and, p_and = stats.mannwhitneyu(
        group_and_yes, group_and_no, alternative='greater')

    print(f"\nEstatística U: {stat_and}")
    print(f"P-valor:        {p_and:.5f}")
    print(f"Nível Alpha:    {alpha}")

    if p_and < alpha:
        print("CONCLUSÃO (AND): Rejeitamos H0.")
        print(">> Vídeos com Call2Go simultâneo (vídeo+canal) geram MAIOR volume de views.")
    else:
        print("CONCLUSÃO (AND): Não rejeitamos H0.")
        print(">> Sem evidência de diferença estatística com lógica AND.")


if __name__ == "__main__":
    run_hypothesis_test()
