import os
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')


def run_spotify_impact_test():
    print("Iniciando Análise de Impacto Cross-Platform (YouTube -> Spotify)...")

    # Conecta ao Data Warehouse
    conn = sqlite3.connect("data/processed/call2go.db")

    # Trazemos a métrica máxima de popularidade do Spotify atrelada ao artista e os tipos de vídeo dele
    query = """
    SELECT 
        y.has_call2go_or,
        y.has_call2go,
        y.view_count,
        s.popularity
    FROM fact_yt_videos y
    JOIN dim_artist a ON y.artist_name = a.artist_name
    JOIN fact_spotify_metrics s ON a.spotify_id = s.spotify_id
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("[ERRO] Falha no JOIN. O dataset está vazio.")
        return

    # ---------------------------------------------------------
    # 1. Gráfico de Dispersão (Correlação Views vs Popularity)
    # ---------------------------------------------------------
    plt.figure(figsize=(6, 4))
    sns.scatterplot(
        data=df,
        x='view_count',
        y='popularity',
        hue='has_call2go_or',
        palette='Set1',
        s=100,  # tamanho dos pontos
        alpha=0.7
    )
    plt.xscale('log')
    plt.title("Correlação entre Views no YouTube e Popularidade no Spotify",
              fontsize=14, fontweight='bold')
    plt.xlabel("Visualizações no YouTube (Log)", fontsize=12)
    plt.ylabel("Índice de Popularidade no Spotify (0-100)", fontsize=12)

    plot_path = "data/plots/scatter_cross_platform.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"[OK] Gráfico de dispersão salvo para o TCC em: {plot_path}\n")

    # ---------------------------------------------------------
    # 2. Testes Estatísticos (Popularidade no Spotify)
    # ---------------------------------------------------------
    alpha = 0.05

    # -------------------------------------------------------------- #
    # ANÁLISE PRIMÁRIA: Lógica OR (H3)                               #
    # -------------------------------------------------------------- #
    print("=" * 60)
    print("ANÁLISE PRIMÁRIA — Lógica OR (H3)")
    print("=" * 60)

    group_or_no = df[df['has_call2go_or'] == 0]['popularity']
    group_or_yes = df[df['has_call2go_or'] == 1]['popularity']

    print("--- ESTATÍSTICA DESCRITIVA: POPULARIDADE NO SPOTIFY (OR) ---")
    print(f"Média Pop (OR=0, Sem Call2Go): {group_or_no.mean():.2f}")
    print(f"Média Pop (OR=1, Com Call2Go): {group_or_yes.mean():.2f}\n")

    print("--- RESULTADO DO TESTE DE HIPÓTESE (SPOTIFY - OR) ---")
    stat_or, p_or = stats.mannwhitneyu(
        group_or_yes, group_or_no, alternative='greater')

    print(f"Estatística U: {stat_or}")
    print(f"P-valor:        {p_or:.5f}")

    if p_or < alpha:
        print("CONCLUSÃO (OR): Rejeitamos H0.")
        print(
            ">> Uso de Call2Go (OR) impacta significativamente a popularidade no Spotify.")
    else:
        print("CONCLUSÃO (OR): Não rejeitamos H0.")
        print(">> Sem evidência de diferença significativa com lógica OR. (Excelente para discussão no TCC).")

    # -------------------------------------------------------------- #
    # SUB-ANÁLISE: Lógica AND                                         #
    # -------------------------------------------------------------- #
    print("\n" + "=" * 60)
    print("SUB-ANÁLISE — Lógica AND (vídeo E canal)")
    print("=" * 60)

    group_and_no = df[df['has_call2go'] == 0]['popularity']
    group_and_yes = df[df['has_call2go'] == 1]['popularity']

    print("--- ESTATÍSTICA DESCRITIVA: POPULARIDADE NO SPOTIFY (AND) ---")
    print(f"Média Pop (AND=0, Sem Call2Go): {group_and_no.mean():.2f}")
    print(f"Média Pop (AND=1, Com Call2Go): {group_and_yes.mean():.2f}\n")

    print("--- RESULTADO DO TESTE DE HIPÓTESE (SPOTIFY - AND) ---")
    stat_and, p_and = stats.mannwhitneyu(
        group_and_yes, group_and_no, alternative='greater')

    print(f"Estatística U: {stat_and}")
    print(f"P-valor:        {p_and:.5f}")

    if p_and < alpha:
        print("CONCLUSÃO (AND): Rejeitamos H0.")
        print(">> Uso simultâneo (vídeo+canal) impacta significativamente a popularidade no Spotify.")
    else:
        print("CONCLUSÃO (AND): Não rejeitamos H0.")
        print(">> Sem evidência de diferença significativa com lógica AND.")


if __name__ == "__main__":
    run_spotify_impact_test()
