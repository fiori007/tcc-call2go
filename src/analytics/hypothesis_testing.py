import sqlite3
import pandas as pd
from scipy import stats

def run_hypothesis_test():
    print("Iniciando Teste de Hipótese Estatística (Mann-Whitney U)...")
    
    # Conecta ao Data Warehouse
    conn = sqlite3.connect("data/processed/call2go.db")
    query = "SELECT view_count, call2go_type FROM fact_yt_videos"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Filtra os grupos (ignoramos o link_direto por ter apenas amostra n=1)
    group_none = df[df['call2go_type'] == 'nenhum']['view_count']
    group_implicit = df[df['call2go_type'] == 'texto_implicito']['view_count']
    
    print(f"Tamanho do Grupo de Controle (Sem Chamada): {len(group_none)}")
    print(f"Tamanho do Grupo de Tratamento (Texto Implícito): {len(group_implicit)}")
    
    # Aplica o Teste de Mann-Whitney (não paramétrico)
    # H0 (Hipótese Nula): Não há diferença de views entre os grupos.
    # H1 (Hipótese Alternativa): Vídeos com texto implícito têm MAIS views.
    stat, p_value = stats.mannwhitneyu(group_implicit, group_none, alternative='greater')
    
    print("\n--- RESULTADO DO TESTE ESTATÍSTICO ---")
    print(f"Estatística U: {stat}")
    print(f"P-valor: {p_value:.5f}")
    
    # Nível de significância (Alpha) de 5%
    alpha = 0.05
    print(f"\nNível de Significância (Alpha): {alpha}")
    
    if p_value < alpha:
        print("CONCLUSÃO: Rejeitamos a Hipótese Nula (H0).")
        print(">> Há evidências estatísticas significativas (com 95% de confiança) de que vídeos COM Call2Go implícito geram MAIOR volume de visualizações do que vídeos sem a chamada.")
    else:
        print("CONCLUSÃO: Falhamos em rejeitar a Hipótese Nula (H0).")
        print(">> Não há diferença estatística significativa; o resultado pode ser obra do acaso.")

if __name__ == "__main__":
    run_hypothesis_test()