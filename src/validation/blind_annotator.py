"""
Gerador de CSV cego para anotação humana independente.

Recebe a amostra adversarial (ou qualquer amostra) e gera um CSV
com APENAS os dados brutos -- descrição do vídeo, descrição do canal,
título -- sem nenhuma sugestão, evidência ou pré-anotação do detector.

Isso elimina o viés de confirmação: o anotador humano não sabe o que
a máquina classificou e precisa ler cada descrição manualmente.

Fluxo de uso:
    1. python -m src.validation.adversarial_sampler   (gera amostra)
    2. python -m src.validation.blind_annotator       (gera CSV cego)
    3. Aluno abre o CSV e anota manualmente cada vídeo
    4. Salva como data/validation/ground_truth.csv
    5. python -m src.validation.cross_validator        (calcula métricas)
"""

import os
import json
import pandas as pd


def generate_blind_csv(
    sample_file="data/validation/adversarial_sample.csv",
    raw_file="data/raw/youtube_videos_raw.jsonl",
    output_file="data/validation/blind_annotation.csv"
):
    """
    Gera CSV cego para anotação humana -- sem output do detector.

    Inclui a descrição completa do vídeo e do canal para que o anotador
    possa avaliar corretamente. Remove colunas internas (_stratum etc.).

    Args:
        sample_file: CSV com video_ids da amostra (adversarial ou outra).
        raw_file: JSONL bruto do YouTube para obter descrições completas.
        output_file: CSV de saída para anotação humana cega.

    Returns:
        pd.DataFrame com o CSV gerado, ou None em caso de erro.
    """
    print("=" * 60)
    print("GERADOR DE CSV CEGO PARA ANOTACAO HUMANA")
    print("=" * 60)

    if not os.path.exists(sample_file):
        print(f"[ERRO] Amostra nao encontrada: {sample_file}")
        print("Execute primeiro: python -m src.validation.adversarial_sampler")
        return None

    if not os.path.exists(raw_file):
        print(f"[ERRO] Dados brutos nao encontrados: {raw_file}")
        return None

    # 1. Carrega IDs da amostra
    df_sample = pd.read_csv(sample_file)
    sample_ids = set(df_sample['video_id'].values)
    print(f"  Videos na amostra: {len(sample_ids)}")

    # 2. Carrega dados brutos completos
    raw_data = {}
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line in f:
            video = json.loads(line)
            vid = video.get('video_id')
            if vid in sample_ids:
                raw_data[vid] = video

    found = len(raw_data)
    if found < len(sample_ids):
        missing = len(sample_ids) - found
        print(
            f"  [AVISO] {missing} videos da amostra nao encontrados no JSONL")

    # 3. Monta CSV cego -- ordem aleatorizada (ja vem do adversarial_sampler)
    rows = []
    for _, sample_row in df_sample.iterrows():
        vid = sample_row['video_id']
        raw = raw_data.get(vid, {})

        description = raw.get('description', '') or ''
        channel_desc = raw.get('channel_description', '') or ''

        rows.append({
            # Identificacao
            'video_id': vid,
            'artist_name': sample_row.get('artist_name', ''),
            'title': sample_row.get('title', ''),
            'youtube_url': f'https://www.youtube.com/watch?v={vid}',

            # Dados brutos para analise humana
            'description': description,
            'channel_description': channel_desc,

            # Colunas para preenchimento humano
            'manual_call2go_video': '',       # link_direto / texto_implicito / nenhum
            'manual_call2go_canal': '',       # link_direto / texto_implicito / nenhum
            'manual_call2go_combinado': '',   # link_direto / texto_implicito / nenhum
            'confianca': '',                  # alta / media / baixa
            'notas': '',                      # observacoes do anotador
        })

    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8')

    print(f"\n  CSV cego gerado: {output_file}")
    print(f"  Total de videos: {len(df)}")
    print(f"\n  --- INSTRUCOES PARA O ANOTADOR ---")
    print("  1. Abra o arquivo CSV (blind_annotation.csv)")
    print("  2. Para CADA video, leia as colunas 'description' e 'channel_description'")
    print("  3. Se necessario, abra o link 'youtube_url' no navegador")
    print("  4. Preencha as colunas:")
    print("     - manual_call2go_video: classificacao da DESCRICAO DO VIDEO")
    print("       -> 'link_direto'      : contem link do Spotify (open.spotify.com, spoti.fi, etc.)")
    print("       -> 'texto_implicito'  : menciona Spotify como CTA ('ouca no Spotify')")
    print("       -> 'nenhum'           : nao tem Call2Go na descricao do video")
    print("     - manual_call2go_canal: classificacao da DESCRICAO DO CANAL")
    print("       -> mesmas opcoes acima, aplicadas ao texto do canal")
    print("     - manual_call2go_combinado: classificacao FINAL do video")
    print("       -> se video OU canal tem Call2Go, o combinado tambem tem")
    print("       -> tipo prevalece: link_direto > texto_implicito > nenhum")
    print("     - confianca: 'alta', 'media', ou 'baixa'")
    print("     - notas: qualquer observacao relevante")
    print("  5. Salve como: data/validation/ground_truth.csv")
    print("  6. Execute: python -m src.validation.cross_validator")

    return df


if __name__ == "__main__":
    generate_blind_csv()
