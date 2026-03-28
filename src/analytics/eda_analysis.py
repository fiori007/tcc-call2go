import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def run_analysis():
    print("Iniciando Análise Exploratória de Dados (EDA)...")
    
    # Cria pasta para os gráficos que irão para o TCC
    os.makedirs("data/plots", exist_ok=True)
    
    # Conecta ao Data Warehouse
    conn = sqlite3.connect("data/processed/call2go.db")
    
    # Query SQL: Cruzando os metadados do YouTube com as métricas do Spotify
    query = """
    SELECT 
        y.video_id,
        y.title,
        y.artist_name,
        y.view_count,
        y.has_call2go,
        y.call2go_type,
        s.popularity,
        s.followers
    FROM fact_yt_videos y
    JOIN dim_artist a ON y.artist_name = a.artist_name
    JOIN fact_spotify_metrics s ON a.spotify_id = s.spotify_id
    """
    
    # Executa a query e carrega num DataFrame do Pandas
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("[ERRO] O dataset unificado está vazio. A query falhou no JOIN.")
        return

    print(f"✅ Dados cruzados com sucesso. Total de registros prontos para análise: {len(df)}")
    
    # ---------------------------------------------------------
    # Geração do Gráfico 1: Impacto Estrutural nas Views
    # ---------------------------------------------------------
    # Vamos gerar um Boxplot para entender como a presença do Call2Go 
    # se distribui em relação à audiência (view_count) no YouTube.
    
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))
    
    # O Boxplot é o padrão científico para mostrar distribuição e outliers
    ax = sns.boxplot(x="call2go_type", y="view_count", data=df, hue="call2go_type", palette="Set2", legend=False)
    
    plt.title("Distribuição de Visualizações no YouTube por Estratégia Call2Go", fontsize=14, fontweight='bold')
    plt.yscale('log') # Escala Logarítmica é obrigatória em views para normalizar as discrepâncias
    plt.ylabel("Visualizações (Escala Logarítmica)", fontsize=12)
    plt.xlabel("Classificação da Chamada (Call2Go)", fontsize=12)
    
    plot1_path = "data/plots/boxplot_call2go_views.png"
    plt.savefig(plot1_path, dpi=300, bbox_inches='tight') # DPI 300 exigido por bancas acadêmicas
    print(f"✅ Gráfico gerado e salvo para o TCC em: {plot1_path}")
    
    # ---------------------------------------------------------
    # Estatística Descritiva Matemática
    # ---------------------------------------------------------
    print("\n--- ESTATÍSTICAS DESCRITIVAS (VIEWS POR TIPO) ---")
    # Calcula Média, Mediana, Min, Max e Desvio Padrão das views agrupadas pelo tipo de Call2Go
    stats = df.groupby('call2go_type')['view_count'].describe()
    
    # Formata para evitar notação científica (ex: 1.2e7) e facilitar a leitura
    pd.options.display.float_format = '{:,.2f}'.format
    print(stats[['count', 'mean', '50%', 'std']]) # 50% = Mediana

if __name__ == "__main__":
    run_analysis()