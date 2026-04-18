"""
TCC Call2Go -- Pipeline Orquestrador

Executa todo o pipeline de dados do início ao fim, na ordem correta:

    1. Construção da base de artistas (Charts Q1 2026 cross-platform)
    2. Coleta de vídeos do YouTube (por artista)
    3. Coleta de métricas do Spotify (por artista)
    4. Scraping de links estruturados dos canais (About page)
    5. Detecção de Call2Go (regex nas descrições)
    6. Construção do Data Warehouse (SQLite)
    7. Análise Exploratória (EDA)
    8. Testes de Hipótese (Mann-Whitney U)
    9. Análise de Impacto Cross-Platform
   10. Geração de amostra para validação manual
   11. Validação Cross-Platform Bidirecional (YouTube <-> Spotify)
   12. Censo Excel para validação manual humana

Uso:
    python run_pipeline.py                  # pipeline completo
    python run_pipeline.py --skip-collect   # pula coleta (usa dados existentes)
    python run_pipeline.py --from-step 5    # começa a partir do passo 5
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
        output_file="data/seed/artistas.csv")


def step_02_collect_youtube():
    """Coleta os 30 vídeos mais visualizados por artista no YouTube."""
    from src.collectors.youtube_collector import collect_youtube_data
    collect_youtube_data(max_videos_per_artist=30)


def step_03_collect_spotify():
    """Coleta métricas do Spotify para cada artista."""
    from src.collectors.spotify_collector import collect_spotify_data
    collect_spotify_data()


def step_04_scrape_channel_links():
    """Scraping de links estruturados da aba Sobre dos canais do YouTube."""
    import pandas as pd
    from src.collectors.channel_link_scraper import scrape_all_channels

    df = pd.read_csv('data/seed/artistas.csv')
    artists_channels = {}
    for _, row in df.iterrows():
        if pd.notna(row.get('youtube_channel_id')):
            artists_channels[row['artist_name']] = row['youtube_channel_id']

    scrape_all_channels(artists_channels, force=True)


def step_05_detect_call2go():
    """Aplica detector regex nas descrições dos vídeos."""
    from src.processors.call2go_detector import process_videos
    process_videos()


def step_06_build_database():
    """Constrói o Data Warehouse SQLite."""
    from src.db.db_builder import build_database
    build_database()


def step_07_eda_analysis():
    """Executa análise exploratória de dados."""
    from src.analytics.eda_analysis import run_analysis
    run_analysis()


def step_08_hypothesis_testing():
    """Executa testes de hipótese estatísticos."""
    from src.analytics.hypothesis_testing import run_hypothesis_test
    run_hypothesis_test()


def step_09_spotify_impact():
    """Executa análise de impacto cross-platform."""
    from src.analytics.spotify_impact_analysis import run_spotify_impact_test
    run_spotify_impact_test()


def step_10_generate_sample():
    """Gera amostra para validação manual."""
    from src.validation.sample_generator import generate_validation_sample
    generate_validation_sample()


def step_11_cross_platform_validation():
    """Executa validação cross-platform bidirecional."""
    from src.validation.cross_platform_validator import run_cross_platform_validation
    run_cross_platform_validation()


def step_12_generate_census_excel():
    """Gera censo completo + Excel formatado para validação manual humana."""
    from src.validation.blind_annotator import (
        generate_census_csv, generate_detector_answers)
    from src.validation.excel_formatter import format_blind_annotation

    # Gera CSVs do censo
    generate_census_csv()
    generate_detector_answers()

    # Gera Excel com dropdowns para anotação manual (versão cega)
    format_blind_annotation(
        input_csv="data/validation/blind_annotation_census.csv",
        output_xlsx="data/validation/blind_annotation_census.xlsx",
        census_mode=True)

    # Gera Excel com respostas do detector (versão gabarito, sem dropdowns)
    format_blind_annotation(
        input_csv="data/validation/detector_answers_census.csv",
        output_xlsx="data/validation/detector_answers_census.xlsx",
        census_mode=True,
        readonly_mode=True)


def main():
    parser = argparse.ArgumentParser(
        description="TCC Call2Go -- Pipeline Orquestrador")
    parser.add_argument('--skip-collect', action='store_true',
                        help='Pula etapas de coleta (usa dados existentes)')
    parser.add_argument('--from-step', type=int, default=1,
                        help='Começa a partir de uma etapa específica (1-12)')
    args = parser.parse_args()

    total_steps = 12
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

    # Verifica estado dos dados
    print("\n--- VERIFICAÇÃO DE DADOS ---")
    check_file_exists(".env", "Variáveis de ambiente")
    check_file_exists("data/seed/artistas.csv", "Base de artistas")
    check_file_exists("data/raw/youtube_videos_raw.jsonl", "Vídeos YouTube")
    check_file_exists("data/raw", "Diretório raw")

    steps = [
        (1, "CONSTRUÇÃO DA BASE DE ARTISTAS", step_01_build_artist_base, False),
        (2, "COLETA YOUTUBE", step_02_collect_youtube, False),
        (3, "COLETA SPOTIFY", step_03_collect_spotify, False),
        (4, "SCRAPING LINKS CANAIS (ABOUT PAGE)",
         step_04_scrape_channel_links, False),
        (5, "DETECÇÃO CALL2GO (REGEX)", step_05_detect_call2go, True),
        (6, "CONSTRUÇÃO DO DATA WAREHOUSE", step_06_build_database, True),
        (7, "ANÁLISE EXPLORATÓRIA (EDA)", step_07_eda_analysis, True),
        (8, "TESTE DE HIPÓTESE (MANN-WHITNEY)", step_08_hypothesis_testing, True),
        (9, "ANÁLISE IMPACTO CROSS-PLATFORM", step_09_spotify_impact, True),
        (10, "GERAÇÃO DE AMOSTRA VALIDAÇÃO", step_10_generate_sample, True),
        (11, "VALIDAÇÃO BIDIRECIONAL (YouTube <-> Spotify)",
         step_11_cross_platform_validation, True),
        (12, "CENSO EXCEL PARA VALIDAÇÃO MANUAL",
         step_12_generate_census_excel, True),
    ]

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

        banner(step_num, total_steps, title)
        success = run_step(func, title)
        results[step_num] = "OK" if success else "FALHA"

        if not success and step_num <= 3:
            print(
                f"\n  [AVISO] Etapa de coleta falhou. Tentando continuar com dados existentes...")
            continue

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
        "data/seed/artistas.csv",
        "data/raw/youtube_videos_raw.jsonl",
        "data/raw/channel_links_scraped.json",
        "data/processed/youtube_call2go_flagged.csv",
        "data/processed/call2go.db",
        "data/plots/boxplot_call2go_views.png",
        "data/plots/scatter_cross_platform.png",
        "data/validation/manual_sample.csv",
        "data/validation/direction_a_youtube_to_spotify.png",
        "data/validation/direction_b_spotify_to_youtube.png",
        "data/validation/bidirectional_correlation_matrix.png",
        "data/validation/cross_platform_report.txt",
        "data/validation/blind_annotation_census.csv",
        "data/validation/blind_annotation_census.xlsx",
        "data/validation/detector_answers_census.csv",
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
