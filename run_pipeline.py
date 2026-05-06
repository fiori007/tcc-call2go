"""
TCC Call2Go -- Pipeline Orquestrador

Executa todo o pipeline de dados do início ao fim, na ordem correta:

    1. Construção da base de artistas (Charts Q1 2026 cross-platform)
    2. Coleta de vídeos do YouTube (por artista)
    3. Coleta de métricas do Spotify (por artista)
    4. Coleta de métricas do Last.fm (artistas + charts BR)
    5. Scraping de links estruturados dos canais (About page)
    6. Detecção de Call2Go (regex nas descrições)
    7. Construção do Data Warehouse (SQLite)
    8. Análise Exploratória (EDA)
    9. Testes de Hipótese (Mann-Whitney U)
   10. Análise de Impacto Cross-Platform
   11. Last.fm Bridge — Análise 3 Fontes
   12. Validação Cross-Platform Bidirecional (YouTube <-> Spotify)
   13. Coleta de datas de lançamento das faixas Spotify Q1 2026
   14. Fusão de rankings cross-platform (RRF normalizado, taxonomia estrutural)
   15. Análise temporal charts (YouTube vs Spotify — defasagem de entrada no chart)
   16. Análise de confundidor (Call2Go vs popularidade SP pré-existente)
   17. Coleta Top-K expansion (Fase 19, opcional, --collect-topk-expansion)
   18. ML Classification (Random Forest predizendo Call2Go) -- sklearn
   19. ML Clustering (KMeans + silhouette) -- sklearn
   20. ML PCA 2D (visualização do espaço de artistas) -- sklearn

Uso:
    python run_pipeline.py                          # pipeline completo
    python run_pipeline.py --skip-collect           # pula coleta (usa dados existentes)
    python run_pipeline.py --from-step 5            # começa a partir do passo 5
    python run_pipeline.py --collect-topk-expansion # habilita step 17
    python run_pipeline.py --list-steps             # lista as 20 etapas e sai
"""

import os
import sys
import time
import argparse
from datetime import datetime

# Garante que imports relativos funcionem
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


FORCE_CHANNEL_SCRAPE = False


def banner(step_num, total, title):
    """Imprime banner formatado para cada etapa."""
    width = 60
    print("\n" + "=" * width)
    print(f"  ETAPA {step_num}/{total}: {title}")
    print("=" * width)


def check_file_exists(path, description):
    """Verifica se um arquivo de dados existe."""
    exists = os.path.exists(path)
    status = "OK" if exists else "AUSENTE"
    print(f"  [{status}] {description}: {path}")
    return exists


def run_step(step_func, step_name):
    """Executa uma etapa com tratamento de erro e cronômetro."""
    start = time.time()
    try:
        step_func()
        elapsed = time.time() - start
        print(f"\n  Concluído em {elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n  [FALHA] {step_name} falhou após {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return False


def step_01_build_artist_base():
    """Constrói base de artistas via interseção cross-platform dos charts."""
    from src.processors.chart_processor import run_chart_processing
    from src.collectors.artist_source_builder import (
        build_seed_from_chart_intersection)

    # Fase A: Processa charts e gera CSV de interseção filtrado
    run_chart_processing()

    # Fase B: Enriquece com Spotify/YouTube IDs e salva seed
    build_seed_from_chart_intersection(
        intersection_csv="data/processed/cross_platform_persistent_artists.csv",
        output_file="data/seed/legacy_v1_artistas.csv")


def step_02_collect_youtube():
    """Coleta os 30 vídeos mais visualizados por artista no YouTube."""
    from src.collectors.youtube_collector import collect_youtube_data
    collect_youtube_data(max_videos_per_artist=30)


def step_03_collect_spotify():
    """Coleta métricas do Spotify para cada artista."""
    from src.collectors.spotify_collector import collect_spotify_data
    collect_spotify_data()


def step_04_collect_lastfm():
    """Coleta métricas do Last.fm para cada artista + charts BR."""
    from src.collectors.lastfm_collector import collect_lastfm_data
    from src.collectors.lastfm_chart_collector import collect_lastfm_charts
    collect_lastfm_data()
    collect_lastfm_charts(country="Brazil", total=200)


def step_05_scrape_channel_links():
    """Scraping de links estruturados da aba Sobre dos canais do YouTube."""
    import pandas as pd
    from src.collectors.channel_link_scraper import scrape_all_channels

    df = pd.read_csv('data/seed/legacy_v1_artistas.csv')
    artists_channels = {}
    for _, row in df.iterrows():
        if pd.notna(row.get('youtube_channel_id')):
            artists_channels[row['artist_name']] = row['youtube_channel_id']

    scrape_all_channels(artists_channels, force=FORCE_CHANNEL_SCRAPE)


def step_06_detect_call2go():
    """Aplica detector regex nas descrições dos vídeos."""
    from src.processors.call2go_detector import process_videos
    process_videos()


def step_07_build_database():
    """Constrói o Data Warehouse SQLite."""
    from src.db.db_builder import build_database
    build_database()


def step_08_eda_analysis():
    """Executa análise exploratória de dados."""
    from src.analytics.eda_analysis import run_analysis
    run_analysis()


def step_09_hypothesis_testing():
    """Executa testes de hipótese estatísticos."""
    from src.analytics.hypothesis_testing import run_hypothesis_test
    run_hypothesis_test()


def step_10_spotify_impact():
    """Executa análise de impacto cross-platform."""
    from src.analytics.spotify_impact_analysis import run_spotify_impact_test
    run_spotify_impact_test()


def step_11_lastfm_bridge():
    """Executa análise Last.fm Bridge — 3 fontes cross-platform."""
    from src.analytics.lastfm_bridge_analysis import run_lastfm_bridge_analysis
    run_lastfm_bridge_analysis()


def step_12_cross_platform_validation():
    """Executa validação cross-platform bidirecional (YouTube <-> Spotify)."""
    from src.validation.cross_platform_validator import run_cross_platform_validation
    run_cross_platform_validation()


def step_13_collect_spotify_track_dates():
    """Coleta datas de lançamento das faixas dos charts Spotify Q1 2026."""
    from src.collectors.spotify_track_dates_collector import collect_track_dates
    collect_track_dates()


def step_14_ranking_fusion_analysis():
    """Executa análise de fusão de rankings cross-platform (RRF normalizado)."""
    from src.analytics.ranking_fusion import run_ranking_fusion_analysis
    run_ranking_fusion_analysis()


def step_15_chart_temporal_analysis():
    """Analisa defasagem temporal entre atividade YouTube e entrada no chart Spotify."""
    from src.analytics.chart_temporal_analysis import run_chart_temporal_analysis
    run_chart_temporal_analysis()


def step_16_confounder_analysis():
    """Testa se popularidade Spotify pre-existente confunde H2/H3 (Call2Go)."""
    from src.analytics.confounder_analysis import run_confounder_analysis
    run_confounder_analysis()


def step_17_topk_expansion_collection():
    """Coleta videos dos artistas Top-K que ficaram fora do seed v1 (Fase 19).

    So roda quando --collect-topk-expansion e passado, pois consome quota
    YouTube. Cobertura objetivo: 100% do Top-K (~46/46 artistas).
    """
    from src.collectors.topk_expansion_collector import collect_topk_expansion
    collect_topk_expansion()


def step_18_ml_classification():
    """Random Forest classificador supervisionado para predizer Call2Go (Fase 19)."""
    from src.analytics.ml_classification import run_ml_classification
    run_ml_classification()


def step_19_ml_clustering():
    """KMeans clustering nao-supervisionado de artistas (Fase 19)."""
    from src.analytics.ml_clustering import run_ml_clustering
    run_ml_clustering()


def step_20_ml_pca_analysis():
    """PCA 2D para visualizacao do espaco de artistas Top-K (Fase 19)."""
    from src.analytics.ml_pca_analysis import run_ml_pca_analysis
    run_ml_pca_analysis()


def _print_steps_listing(steps):
    """Imprime a lista numerada de etapas disponiveis (--list-steps)."""
    print("\nEtapas do pipeline:")
    print(f"  {'#':>3}  {'Tipo':<8}  Titulo")
    print(f"  {'-'*3}  {'-'*8}  {'-'*50}")
    for step_num, title, _, can_skip_collect in steps:
        kind = "analise" if can_skip_collect else "coleta"
        print(f"  {step_num:>3}  {kind:<8}  {title}")


def main():
    parser = argparse.ArgumentParser(
        description="TCC Call2Go -- Pipeline Orquestrador")
    parser.add_argument('--skip-collect', action='store_true',
                        help='Pula etapas de coleta (usa dados existentes)')
    parser.add_argument('--from-step', type=int, default=1,
                        help='Comeca a partir de uma etapa especifica (1-15)')
    parser.add_argument('--force-channel-scrape', action='store_true',
                        help='Forca re-scraping dos canais (ignora cache da etapa 5)')
    parser.add_argument('--list-steps', action='store_true',
                        help='Lista as etapas e sai sem executar')
    parser.add_argument('--dry-run', action='store_true',
                        help='Mostra o plano de execucao sem rodar nenhuma etapa')
    parser.add_argument('--strict', action='store_true',
                        help='Para o pipeline na primeira falha (default: continua)')
    parser.add_argument('--collect-topk-expansion', action='store_true',
                        help='Habilita step 17 (coleta Top-K expansion, consome quota YouTube)')
    args = parser.parse_args()

    global FORCE_CHANNEL_SCRAPE
    FORCE_CHANNEL_SCRAPE = args.force_channel_scrape

    total_steps = 20
    start_time = time.time()

    print("\n" + "#" * 60)
    print("#" + " " * 58 + "#")
    print("#    TCC CALL2GO -- PIPELINE DE DADOS COMPLETO" + " " * 13 + "#")
    print("#" + " " * 58 + "#")
    print("#" * 60)
    print(f"\n  Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Diretório: {PROJECT_ROOT}")
    print(f"  Python: {sys.version.split()[0]}")

    if args.skip_collect:
        print("  Modo: --skip-collect (pula coleta, usa dados existentes)")
    if args.from_step > 1:
        print(f"  Modo: --from-step {args.from_step}")
    if args.force_channel_scrape:
        print("  Modo: --force-channel-scrape (ignora cache da etapa 5)")

    # Verifica estado dos dados
    print("\n--- VERIFICAÇÃO DE DADOS ---")
    check_file_exists(".env", "Variáveis de ambiente")
    check_file_exists("data/seed/legacy_v1_artistas.csv", "Base de artistas")
    check_file_exists("data/raw/youtube_videos_raw.jsonl", "Vídeos YouTube")
    check_file_exists("data/raw", "Diretório raw")

    steps = [
        (1,  "CONSTRUCAO DA BASE DE ARTISTAS",
         step_01_build_artist_base,          False),
        (2,  "COLETA YOUTUBE",
         step_02_collect_youtube,             False),
        (3,  "COLETA SPOTIFY",
         step_03_collect_spotify,             False),
        (4,  "COLETA LAST.FM (ARTISTAS + CHARTS BR)",
         step_04_collect_lastfm,              False),
        (5,  "SCRAPING LINKS CANAIS (ABOUT PAGE)",
         step_05_scrape_channel_links,        False),
        (6,  "DETECCAO CALL2GO (REGEX)",
         step_06_detect_call2go,              True),
        (7,  "CONSTRUCAO DO DATA WAREHOUSE",
         step_07_build_database,              True),
        (8,  "ANALISE EXPLORATORIA (EDA)",
         step_08_eda_analysis,                True),
        (9,  "TESTE DE HIPOTESE (MANN-WHITNEY)",
         step_09_hypothesis_testing,          True),
        (10, "ANALISE IMPACTO CROSS-PLATFORM",
         step_10_spotify_impact,              True),
        (11, "LAST.FM BRIDGE (3 FONTES)",
         step_11_lastfm_bridge,               True),
        (12, "VALIDACAO BIDIRECIONAL (YouTube <-> Spotify)",
         step_12_cross_platform_validation,  True),
        (13, "COLETA DATAS FAIXAS SPOTIFY",
         step_13_collect_spotify_track_dates, False),
        (14, "FUSAO DE RANKINGS + ANALISE TEMPORAL",
         step_14_ranking_fusion_analysis,     True),
        (15, "ANALISE TEMPORAL CHARTS (YouTube vs Spotify)",
         step_15_chart_temporal_analysis,     True),
        (16, "ANALISE DE CONFUNDIDOR (Call2Go vs popularidade SP)",
         step_16_confounder_analysis,         True),
        (17, "COLETA TOP-K EXPANSION (Fase 19)",
         step_17_topk_expansion_collection,   False),
        (18, "ML CLASSIFICATION (Random Forest)",
         step_18_ml_classification,           True),
        (19, "ML CLUSTERING (KMeans + silhouette)",
         step_19_ml_clustering,               True),
        (20, "ML PCA 2D (visualizacao)",
         step_20_ml_pca_analysis,             True),
    ]

    # --list-steps: imprime e sai
    if args.list_steps:
        _print_steps_listing(steps)
        return

    results = {}

    for step_num, title, func, can_skip_collect in steps:
        if step_num < args.from_step:
            print(f"\n  [SKIP] Etapa {step_num}: {title}")
            results[step_num] = "SKIP"
            continue

        if args.skip_collect and not can_skip_collect:
            print(f"\n  [SKIP] Etapa {step_num}: {title} (--skip-collect)")
            results[step_num] = "SKIP"
            continue

        # Step 17 (Top-K expansion) so roda com flag explicita
        if step_num == 17 and not args.collect_topk_expansion:
            print(f"\n  [SKIP] Etapa {step_num}: {title} (sem --collect-topk-expansion)")
            results[step_num] = "SKIP"
            continue

        if args.dry_run:
            print(f"\n  [DRY-RUN] Etapa {step_num}: {title}")
            results[step_num] = "DRY-RUN"
            continue

        banner(step_num, total_steps, title)
        success = run_step(func, title)
        results[step_num] = "OK" if success else "FALHA"

        if not success:
            # --strict: para na primeira falha (em qualquer etapa)
            if args.strict:
                print(f"\n  [STRICT] Falha na etapa {step_num}, abortando pipeline.")
                break
            # Padrao: tolerante para coleta (1-4), strict para analise (5+)
            if step_num <= 4:
                print(
                    f"\n  [AVISO] Etapa de coleta falhou. Tentando continuar com dados existentes...")
                continue
            # Etapas analiticas: falha cascateia para as seguintes via dependencias.
            # Continua mas sinaliza claramente.
            print(f"\n  [AVISO] Etapa analitica {step_num} falhou -- subsequentes podem falhar tambem.")

    # Relatório final
    total_time = time.time() - start_time
    print("\n" + "#" * 60)
    print("#    RELATÓRIO FINAL DO PIPELINE")
    print("#" * 60)
    print(f"\n  Tempo total: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"\n  {'Etapa':<45} {'Status'}")
    print(f"  {'-'*45} {'-'*8}")

    for step_num, title, _, _ in steps:
        status = results.get(step_num, "N/A")
        icon = {"OK": "[OK]", "FALHA": "[FALHA]",
                "SKIP": "[SKIP]"}.get(status, "[?]")
        print(f"  {icon} {step_num:2d}. {title:<40} {status}")

    # Verifica outputs finais
    print(f"\n--- OUTPUTS GERADOS ---")
    output_files = [
        # Raw data
        "data/seed/legacy_v1_artistas.csv",
        "data/raw/youtube_videos_raw.jsonl",
        "data/raw/channel_links_scraped.json",
        "data/raw/spotify_track_dates_Q1_2026.csv",
        # Processed
        "data/processed/youtube_call2go_flagged.csv",
        "data/processed/call2go.db",
        "data/processed/ranking_fusion_scores.csv",
        # Validation -- confounder analysis (step 16)
        "data/validation/confounder_analysis.txt",
        "data/validation/confounder_analysis_strat.csv",
        # Fase 19 -- ML outputs
        "data/processed/artist_clusters.csv",
        "data/validation/ml_classification_report.txt",
        "data/validation/ml_clustering_report.txt",
        "data/validation/ml_pca_report.txt",
        "data/plots/ml_call2go_roc.png",
        "data/plots/ml_call2go_feature_importance.png",
        "data/plots/ml_clustering_pca.png",
        "data/plots/ml_pca_artists.png",
        # Plots
        "data/plots/boxplot_call2go_views.png",
        "data/plots/scatter_cross_platform.png",
        "data/plots/rank_comparison_3sources.png",
        "data/plots/callgo_by_genre.png",
        "data/plots/mannwhitney_lastfm.png",
        "data/plots/scatter_3source_bidirectional.png",
        "data/plots/presence_heatmap_spotify.png",
        "data/plots/presence_heatmap_youtube.png",
        "data/plots/rank_evolution_spotify.png",
        "data/plots/fusion_score_by_call2go.png",
        "data/plots/fusion_lastfm_correlation.png",
        "data/plots/temporal_lag_analysis.png",
        "data/plots/chart_temporal_lag_histogram.png",
        "data/plots/chart_temporal_windows.png",
        "data/plots/chart_temporal_correlation.png",
        # Validation
        "data/validation/cross_platform_report.txt",
        "data/validation/artist_cross_platform_profile.csv",
        "data/validation/lastfm_bridge_report.txt",
        "data/validation/three_way_intersection.csv",
        "data/validation/track_level_matching.csv",
        "data/validation/ranking_fusion_report.txt",
        "data/validation/seed_matching_diagnostic.csv",
        "data/validation/chart_temporal_results.csv",
    ]

    for f in output_files:
        if os.path.exists(f):
            size = os.path.getsize(f)
            size_str = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
            print(f"  [OK] {f} ({size_str})")
        else:
            print(f"  [FALTA] {f}")

    print(f"\n  Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 60)


if __name__ == "__main__":
    main()
