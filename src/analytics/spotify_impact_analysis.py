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
        y.call2go_type,
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
        hue='call2go_type',
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
    # 2. Teste Estatístico (Popularidade no Spotify)
    # ---------------------------------------------------------
    group_none = df[df['call2go_type'] == 'nenhum']['popularity']
    group_call2go = df[df['call2go_type'] != 'nenhum']['popularity']

    print("--- ESTATÍSTICA DESCRITIVA: POPULARIDADE NO SPOTIFY ---")
    print(f"Média Pop (Sem Call2Go): {group_none.mean():.2f}")
    print(f"Média Pop (Com Call2Go): {group_call2go.mean():.2f}\n")

    print("--- RESULTADO DO TESTE DE HIPÓTESE (SPOTIFY) ---")
    # Testa se a popularidade é maior nos casos em que houve Call2Go
    stat, p_value = stats.mannwhitneyu(
        group_call2go, group_none, alternative='greater')

    print(f"Estatística U: {stat}")
    print(f"P-valor: {p_value:.5f}")

    alpha = 0.05
    if p_value < alpha:
        print("CONCLUSÃO CROSS-PLATFORM: Rejeitamos a Hipótese Nula (H0).")
        print(">> O uso de Call2Go no YouTube gera um impacto estatisticamente significativo NA POPULARIDADE DO SPOTIFY.")
    else:
        print("CONCLUSÃO CROSS-PLATFORM: Falhamos em rejeitar a Hipótese Nula (H0).")
        print(">> Embora o Call2Go gere mais views no YouTube, não há evidências de que essa conversão se reflita em uma pontuação de popularidade maior no Spotify de forma imediata. (Isso é excelente para discussão no TCC).")


if __name__ == "__main__":
    run_spotify_impact_test()
