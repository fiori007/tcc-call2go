"""
VALIDAÇÃO CROSS-PLATFORM BIDIRECIONAL — A "VOLTA"

A questão central: a relação entre YouTube e Spotify é unidirecional ou bidirecional?

Direção A — YouTube → Spotify:
    Vídeos com Call2Go (links/menções ao Spotify) → Impacto nas métricas do Spotify?
    Intensidade de Call2Go por artista → Correlação com popularidade/seguidores Spotify?

Direção B — Spotify → YouTube (A VOLTA):
    Popularidade no Spotify → Impacto nas métricas do YouTube?
    Seguidores Spotify → Correlação com views/likes/comentários no YouTube?
    Spotify como FONTE de tráfego para YouTube?

Resultado esperado: classificar a relação cross-platform como:
    - Unidirecional (só YouTube → Spotify)
    - Bidirecional (feedback loop — ambas as plataformas se alimentam)
    - Independente (sem correlação significativa)
"""

import os
import glob
import json
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


def load_youtube_data(flagged_file="data/processed/youtube_call2go_flagged.csv",
                      raw_file="data/raw/youtube_videos_raw.jsonl"):
    """Carrega dados do YouTube (flagged + raw para descrições)."""
    if not os.path.exists(flagged_file):
        print(f"[ERRO] Arquivo não encontrado: {flagged_file}")
        print("Execute primeiro: python -m src.processors.call2go_detector")
        return None

    df = pd.read_csv(flagged_file)

    # Garante tipos numéricos
    for col in ['view_count', 'like_count', 'comment_count']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    return df


def load_spotify_data(data_dir="data/raw"):
    """Carrega o arquivo mais recente de métricas Spotify."""
    pattern = os.path.join(data_dir, "spotify_metrics_*.csv")
    files = glob.glob(pattern)
    if not files:
        print(
            f"[ERRO] Nenhum arquivo de métricas Spotify encontrado em {data_dir}")
        return None

    latest = max(files)
    print(f"Usando métricas Spotify de: {os.path.basename(latest)}")
    df = pd.read_csv(latest)

    for col in ['followers', 'popularity']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df


def build_artist_profile(df_yt, df_sp):
    """
    Constrói perfil por artista com métricas de AMBAS as plataformas.
    Este é o dataset central para a análise bidirecional.
    """

    # --- Métricas YouTube por artista ---
    yt_agg = df_yt.groupby('artist_name').agg(
        total_videos=('video_id', 'count'),
        videos_com_call2go=('has_call2go', 'sum'),
        total_views=('view_count', 'sum'),
        avg_views=('view_count', 'mean'),
        median_views=('view_count', 'median'),
        total_likes=('like_count', 'sum'),
        avg_likes=('like_count', 'mean'),
        total_comments=('comment_count', 'sum'),
        avg_comments=('comment_count', 'mean'),
    ).reset_index()

    # Taxa de Call2Go (intensidade da estratégia)
    yt_agg['call2go_rate'] = yt_agg['videos_com_call2go'] / \
        yt_agg['total_videos']

    # Detalhamento por tipo
    type_counts = df_yt.groupby(['artist_name', 'call2go_type']).size().unstack(
        fill_value=0).reset_index()
    for col in ['link_direto', 'texto_implicito', 'nenhum']:
        if col not in type_counts.columns:
            type_counts[col] = 0

    yt_agg = yt_agg.merge(type_counts[[
                          'artist_name', 'link_direto', 'texto_implicito']], on='artist_name', how='left')
    yt_agg['link_rate'] = yt_agg['link_direto'] / yt_agg['total_videos']
    yt_agg['text_rate'] = yt_agg['texto_implicito'] / yt_agg['total_videos']

    # Engagement médio de vídeos COM vs SEM Call2Go
    for artist in yt_agg['artist_name'].values:
        mask = df_yt['artist_name'] == artist
        with_c2g = df_yt[mask & (df_yt['has_call2go'] == 1)]
        without_c2g = df_yt[mask & (df_yt['has_call2go'] == 0)]

        yt_agg.loc[yt_agg['artist_name'] == artist,
                   'avg_views_com_c2g'] = with_c2g['view_count'].mean() if len(with_c2g) > 0 else 0
        yt_agg.loc[yt_agg['artist_name'] == artist, 'avg_views_sem_c2g'] = without_c2g['view_count'].mean(
        ) if len(without_c2g) > 0 else 0

    # --- Merge com Spotify ---
    df_sp_cols = df_sp[['artist_name', 'followers', 'popularity']].copy()
    df_profile = yt_agg.merge(df_sp_cols, on='artist_name', how='inner')

    # Engajamento total (likes + comments)
    df_profile['total_engagement'] = df_profile['total_likes'] + \
        df_profile['total_comments']
    df_profile['avg_engagement'] = df_profile['avg_likes'] + \
        df_profile['avg_comments']

    return df_profile


def direction_a_youtube_to_spotify(df_profile, df_yt, output_dir):
    """
    DIREÇÃO A: YouTube → Spotify
    Pergunta: A intensidade de Call2Go nos vídeos do YouTube se correlaciona
    com métricas mais altas no Spotify?
    """
    print("\n" + "=" * 60)
    print("DIREÇÃO A: YouTube → Spotify")
    print("Pergunta: Call2Go no YouTube impacta o Spotify?")
    print("=" * 60)

    results = {}

    # 1. Correlação: taxa de Call2Go ↔ popularidade Spotify
    if len(df_profile) >= 3:
        corr_pop, p_pop = stats.spearmanr(
            df_profile['call2go_rate'], df_profile['popularity'])
        corr_fol, p_fol = stats.spearmanr(
            df_profile['call2go_rate'], df_profile['followers'])

        print(
            f"\n  Call2Go Rate ↔ Spotify Popularity: ρ={corr_pop:.3f}, p={p_pop:.4f}")
        print(
            f"  Call2Go Rate ↔ Spotify Followers:  ρ={corr_fol:.3f}, p={p_fol:.4f}")

        results['call2go_vs_popularity'] = {'rho': corr_pop, 'p': p_pop}
        results['call2go_vs_followers'] = {'rho': corr_fol, 'p': p_fol}

    # 2. Mann-Whitney: views de vídeos COM vs SEM Call2Go
    with_c2g = df_yt[df_yt['has_call2go'] == 1]['view_count'].astype(float)
    without_c2g = df_yt[df_yt['has_call2go'] == 0]['view_count'].astype(float)

    if len(with_c2g) > 0 and len(without_c2g) > 0:
        u_stat, u_p = stats.mannwhitneyu(
            with_c2g, without_c2g, alternative='two-sided')
        print(f"\n  Mann-Whitney (Views: com Call2Go vs sem):")
        print(
            f"    Mediana COM: {with_c2g.median():,.0f} | SEM: {without_c2g.median():,.0f}")
        print(f"    U={u_stat:.0f}, p={u_p:.5f}")
        results['views_mannwhitney'] = {'U': u_stat, 'p': u_p,
                                        'median_with': with_c2g.median(),
                                        'median_without': without_c2g.median()}

    # 3. Gráfico: Call2Go Rate vs Spotify Popularity (por artista)
    fig, axes = plt.subplots(1, 2, figsize=(5.9, 4))

    axes[0].scatter(df_profile['call2go_rate'], df_profile['popularity'],
                    s=100, c='#1DB954', edgecolors='black')
    for _, row in df_profile.iterrows():
        axes[0].annotate(row['artist_name'], (row['call2go_rate'], row['popularity']),
                         textcoords="offset points", xytext=(5, 5), fontsize=8)
    axes[0].set_xlabel('Taxa de Call2Go (YouTube)', fontsize=11)
    axes[0].set_ylabel('Popularidade (Spotify)', fontsize=11)
    axes[0].set_title(
        'YouTube → Spotify\nCall2Go Rate vs Popularidade', fontsize=12, fontweight='bold')

    axes[1].scatter(df_profile['call2go_rate'], df_profile['followers'],
                    s=100, c='#1DB954', edgecolors='black')
    for _, row in df_profile.iterrows():
        axes[1].annotate(row['artist_name'], (row['call2go_rate'], row['followers']),
                         textcoords="offset points", xytext=(5, 5), fontsize=8)
    axes[1].set_xlabel('Taxa de Call2Go (YouTube)', fontsize=11)
    axes[1].set_ylabel('Seguidores (Spotify)', fontsize=11)
    axes[1].set_title(
        'YouTube → Spotify\nCall2Go Rate vs Seguidores', fontsize=12, fontweight='bold')
    axes[1].yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f'{x/1e6:.1f}M'))

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "direction_a_youtube_to_spotify.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n  Gráfico salvo: {plot_path}")

    return results


def direction_b_spotify_to_youtube(df_profile, df_yt, df_sp, output_dir):
    """
    DIREÇÃO B: Spotify → YouTube (A VOLTA!)
    Pergunta: A popularidade no Spotify se correlaciona com mais engajamento
    nos vídeos do YouTube? Spotify gera tráfego de volta?
    """
    print("\n" + "=" * 60)
    print("DIREÇÃO B: Spotify → YouTube (A VOLTA)")
    print("Pergunta: Popularidade no Spotify impacta o YouTube?")
    print("=" * 60)

    results = {}

    # 1. Correlação por artista: Spotify metrics ↔ YouTube metrics
    if len(df_profile) >= 3:
        pairs = [
            ('popularity', 'avg_views', 'Spotify Pop ↔ YouTube Avg Views'),
            ('popularity', 'avg_engagement', 'Spotify Pop ↔ YouTube Avg Engagement'),
            ('followers', 'avg_views', 'Spotify Followers ↔ YouTube Avg Views'),
            ('followers', 'total_views', 'Spotify Followers ↔ YouTube Total Views'),
            ('followers', 'avg_engagement',
             'Spotify Followers ↔ YouTube Avg Engagement'),
        ]

        print("\n  Correlações Spotify → YouTube (Spearman):")
        for sp_col, yt_col, label in pairs:
            rho, p = stats.spearmanr(df_profile[sp_col], df_profile[yt_col])
            sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "n.s."
            print(f"    {label}: ρ={rho:.3f}, p={p:.4f} {sig}")
            results[f'{sp_col}_vs_{yt_col}'] = {'rho': rho, 'p': p}

    # 2. Análise por vídeo: Spotify popularity do artista vs views do vídeo
    df_video = df_yt.merge(
        df_sp[['artist_name', 'popularity', 'followers']], on='artist_name', how='inner')

    if len(df_video) > 10:
        rho_vid, p_vid = stats.spearmanr(
            df_video['popularity'], df_video['view_count'].astype(float))
        print(f"\n  Por vídeo (N={len(df_video)}):")
        print(
            f"    Spotify Pop ↔ YouTube Views: ρ={rho_vid:.3f}, p={p_vid:.5f}")
        results['per_video_pop_vs_views'] = {
            'rho': rho_vid, 'p': p_vid, 'n': len(df_video)}

    # 3. Gráfico: Spotify metrics → YouTube metrics
    fig, axes = plt.subplots(1, 2, figsize=(5.9, 4))

    # Popularity → Avg Views
    axes[0].scatter(df_profile['popularity'], df_profile['avg_views'],
                    s=100, c='#FF0000', edgecolors='black')
    for _, row in df_profile.iterrows():
        axes[0].annotate(row['artist_name'], (row['popularity'], row['avg_views']),
                         textcoords="offset points", xytext=(5, 5), fontsize=8)
    axes[0].set_xlabel('Popularidade (Spotify)', fontsize=11)
    axes[0].set_ylabel('Média de Views (YouTube)', fontsize=11)
    axes[0].set_title(
        'Spotify → YouTube (A VOLTA)\nPopularidade vs Média de Views', fontsize=12, fontweight='bold')
    axes[0].yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f'{x/1e3:.0f}K'))

    # Followers → Avg Engagement
    axes[1].scatter(df_profile['followers'], df_profile['avg_engagement'],
                    s=100, c='#FF0000', edgecolors='black')
    for _, row in df_profile.iterrows():
        axes[1].annotate(row['artist_name'], (row['followers'], row['avg_engagement']),
                         textcoords="offset points", xytext=(5, 5), fontsize=8)
    axes[1].set_xlabel('Seguidores (Spotify)', fontsize=11)
    axes[1].set_ylabel('Engajamento Médio (YouTube)', fontsize=11)
    axes[1].set_title(
        'Spotify → YouTube (A VOLTA)\nSeguidores vs Engajamento', fontsize=12, fontweight='bold')
    axes[1].xaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f'{x/1e6:.0f}M'))

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "direction_b_spotify_to_youtube.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n  Gráfico salvo: {plot_path}")

    return results


def bidirectional_synthesis(results_a, results_b, df_profile, output_dir):
    """
    SÍNTESE: Classifica a relação cross-platform como:
    - Bidirecional (feedback loop)
    - Unidirecional (só um sentido)
    - Independente (sem correlação)
    """
    print("\n" + "=" * 60)
    print("SÍNTESE BIDIRECIONAL — CLASSIFICAÇÃO DA RELAÇÃO")
    print("=" * 60)

    alpha = 0.10  # Relaxado para amostras pequenas

    # Avalia Direção A
    a_sig = False
    if 'call2go_vs_popularity' in results_a:
        a_sig = results_a['call2go_vs_popularity']['p'] < alpha
    if 'views_mannwhitney' in results_a:
        a_sig = a_sig or results_a['views_mannwhitney']['p'] < alpha

    # Avalia Direção B
    b_sig = False
    b_keys = [k for k in results_b if k.startswith(
        'popularity_vs') or k.startswith('followers_vs')]
    for k in b_keys:
        if results_b[k]['p'] < alpha:
            b_sig = True
            break

    # Classificação
    if a_sig and b_sig:
        classification = "BIDIRECIONAL (Feedback Loop)"
        interpretation = ("Evidências sugerem que YouTube e Spotify se alimentam mutuamente. "
                          "Call2Go no YouTube correlaciona com métricas Spotify, E "
                          "métricas Spotify correlacionam com engajamento no YouTube.")
    elif a_sig and not b_sig:
        classification = "UNIDIRECIONAL: YouTube → Spotify"
        interpretation = ("Call2Go no YouTube mostra correlação com métricas Spotify, "
                          "mas NÃO há evidência de que Spotify impacte de volta o YouTube.")
    elif not a_sig and b_sig:
        classification = "UNIDIRECIONAL: Spotify → YouTube"
        interpretation = ("Métricas do Spotify correlacionam com engajamento no YouTube, "
                          "mas Call2Go no YouTube não demonstra impacto significativo no Spotify.")
    else:
        classification = "INDEPENDENTE"
        interpretation = ("Não foram encontradas correlações significativas em nenhuma direção. "
                          "As plataformas parecem operar de forma independente nesta amostra.")

    print(f"\n  CLASSIFICAÇÃO: {classification}")
    print(f"  α = {alpha}")
    print(f"\n  Interpretação: {interpretation}")

    # Gráfico de síntese — Heatmap de correlação bidirecional
    sp_cols = ['popularity', 'followers']
    yt_cols = ['avg_views', 'avg_likes',
               'avg_comments', 'call2go_rate', 'total_views']

    existing_sp = [c for c in sp_cols if c in df_profile.columns]
    existing_yt = [c for c in yt_cols if c in df_profile.columns]

    if len(existing_sp) > 0 and len(existing_yt) > 0:
        corr_data = []
        for sp in existing_sp:
            row_corrs = []
            for yt in existing_yt:
                if len(df_profile) >= 3:
                    rho, _ = stats.spearmanr(df_profile[sp], df_profile[yt])
                    row_corrs.append(rho)
                else:
                    row_corrs.append(0)
            corr_data.append(row_corrs)

        corr_matrix = pd.DataFrame(
            corr_data, index=existing_sp, columns=existing_yt)

        fig, ax = plt.subplots(figsize=(5.9, 4))
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='RdYlGn', center=0,
                    vmin=-1, vmax=1, ax=ax, linewidths=0.5,
                    xticklabels=[c.replace('_', ' ').title()
                                 for c in existing_yt],
                    yticklabels=[c.replace('_', ' ').title() for c in existing_sp])
        ax.set_title(f'Matriz de Correlação Bidirecional\nClassificação: {classification}',
                     fontsize=13, fontweight='bold')
        ax.set_xlabel('Métricas YouTube', fontsize=11)
        ax.set_ylabel('Métricas Spotify', fontsize=11)

        plt.tight_layout()
        plot_path = os.path.join(
            output_dir, "bidirectional_correlation_matrix.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"\n  Heatmap salvo: {plot_path}")

    return {
        'classification': classification,
        'interpretation': interpretation,
        'direction_a_significant': a_sig,
        'direction_b_significant': b_sig,
        'alpha': alpha,
    }


def generate_report(df_profile, results_a, results_b, synthesis, output_dir):
    """Salva relatório completo em CSV e texto."""
    # Perfil por artista
    profile_path = os.path.join(
        output_dir, "artist_cross_platform_profile.csv")
    df_profile.to_csv(profile_path, index=False)
    print(f"\n  Perfil por artista salvo: {profile_path}")

    # Relatório textual
    report_path = os.path.join(output_dir, "cross_platform_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("RELATÓRIO DE VALIDAÇÃO CROSS-PLATFORM BIDIRECIONAL\n")
        f.write("=" * 60 + "\n\n")

        f.write("CLASSIFICAÇÃO: " + synthesis['classification'] + "\n")
        f.write("Nível de significância: α = " +
                str(synthesis['alpha']) + "\n\n")
        f.write("INTERPRETAÇÃO:\n" + synthesis['interpretation'] + "\n\n")

        f.write("-" * 60 + "\n")
        f.write("DIREÇÃO A: YouTube → Spotify\n")
        f.write("-" * 60 + "\n")
        for k, v in results_a.items():
            f.write(f"  {k}: {v}\n")

        f.write("\n" + "-" * 60 + "\n")
        f.write("DIREÇÃO B: Spotify → YouTube (A VOLTA)\n")
        f.write("-" * 60 + "\n")
        for k, v in results_b.items():
            f.write(f"  {k}: {v}\n")

        f.write("\n" + "-" * 60 + "\n")
        f.write("PERFIL POR ARTISTA\n")
        f.write("-" * 60 + "\n")
        for _, row in df_profile.iterrows():
            f.write(f"\n  {row['artist_name']}:\n")
            f.write(f"    YouTube: {row['total_videos']} vídeos, {row['call2go_rate']:.0%} Call2Go, "
                    f"avg views {row['avg_views']:,.0f}\n")
            f.write(
                f"    Spotify: pop={row['popularity']}, followers={row['followers']:,.0f}\n")
            f.write(f"    Views COM Call2Go: {row['avg_views_com_c2g']:,.0f} | "
                    f"SEM: {row['avg_views_sem_c2g']:,.0f}\n")

    print(f"  Relatório textual salvo: {report_path}")


def run_cross_platform_validation():
    """Executa a validação cross-platform bidirecional completa."""
    print("=" * 60)
    print("VALIDAÇÃO CROSS-PLATFORM BIDIRECIONAL")
    print("A 'VOLTA': YouTube ↔ Spotify")
    print("=" * 60)

    # 1. Carrega dados
    df_yt = load_youtube_data()
    df_sp = load_spotify_data()

    if df_yt is None or df_sp is None:
        return

    print(
        f"\n  YouTube: {len(df_yt)} vídeos, {df_yt['artist_name'].nunique()} artistas")
    print(f"  Spotify: {len(df_sp)} artistas")

    # 2. Constrói perfil bidirecional
    df_profile = build_artist_profile(df_yt, df_sp)
    print(
        f"  Perfil cruzado: {len(df_profile)} artistas com dados em AMBAS as plataformas")

    # 3. Prepara diretório de saída
    output_dir = "data/validation"
    os.makedirs(output_dir, exist_ok=True)

    # 4. Direção A: YouTube → Spotify
    results_a = direction_a_youtube_to_spotify(df_profile, df_yt, output_dir)

    # 5. Direção B: Spotify → YouTube (A VOLTA)
    results_b = direction_b_spotify_to_youtube(
        df_profile, df_yt, df_sp, output_dir)

    # 6. Síntese bidirecional
    synthesis = bidirectional_synthesis(
        results_a, results_b, df_profile, output_dir)

    # 7. Relatório
    generate_report(df_profile, results_a, results_b, synthesis, output_dir)

    print("\n" + "=" * 60)
    print("VALIDAÇÃO BIDIRECIONAL CONCLUÍDA")
    print(f"Resultados em: {output_dir}/")
    print("=" * 60)


if __name__ == "__main__":
    run_cross_platform_validation()
