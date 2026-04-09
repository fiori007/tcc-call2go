import os
import json
import pandas as pd
import random


def generate_validation_sample(input_file="data/raw/youtube_videos_raw.jsonl",
                               output_file="data/validation/manual_sample.csv",
                               sample_size=50,
                               seed=42):
    """
    Gera uma amostra aleatória de vídeos para validação manual humana.

    Esta é a etapa que o orientador chamou de 'base de verdade' (ground truth):
    o aluno deve classificar manualmente uma amostra ANTES de confiar no
    classificador automatizado. Isso cria um padrão de referência independente.

    O seed fixo garante reprodutibilidade -- qualquer pesquisador que rode
    este script obterá a mesma amostra.

    Args:
        input_file: Caminho do JSONL bruto do YouTube.
        output_file: Caminho do CSV de saída para anotação manual.
        sample_size: Quantidade de vídeos na amostra.
        seed: Seed para reprodutibilidade.
    """
    print("=" * 60)
    print("GERAÇÃO DE AMOSTRA PARA VALIDAÇÃO MANUAL (GROUND TRUTH)")
    print("=" * 60)

    if not os.path.exists(input_file):
        print(f"[ERRO] Arquivo {input_file} não encontrado.")
        return

    # Carrega todos os vídeos
    videos = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            videos.append(json.loads(line))

    total = len(videos)
    actual_sample = min(sample_size, total)

    # Amostra aleatória com seed fixo
    random.seed(seed)
    sample = random.sample(videos, actual_sample)

    # Monta o DataFrame com colunas para anotação manual
    rows = []
    for v in sample:
        description = v.get('description', '')
        channel_desc = v.get('channel_description', '')
        rows.append({
            'video_id': v.get('video_id'),
            'artist_name': v.get('artist_name'),
            'title': v.get('title'),
            'description_preview': description[:300] if description else '',
            'full_description_length': len(description) if description else 0,
            'channel_description_preview': channel_desc[:300] if channel_desc else '',
            'has_spotify_link': '',       # PREENCHER MANUALMENTE: sim/nao
            'has_spotify_text': '',       # PREENCHER MANUALMENTE: sim/nao
            # PREENCHER MANUALMENTE: link_direto / texto_implicito / nenhum
            'manual_call2go_type': '',
            # PREENCHER MANUALMENTE: link_direto / texto_implicito / nenhum
            'manual_channel_call2go_type': '',
            'notes': ''                   # PREENCHER MANUALMENTE: observações
        })

    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8')

    print(f"\n[OK] Amostra gerada: {actual_sample} vídeos de {total} total")
    print(f"[OK] Arquivo salvo em: {output_file}")
    print(f"[OK] Seed utilizado: {seed}")
    print(f"\n--- INSTRUÇÕES PARA O ANOTADOR ---")
    print("1. Abra o arquivo CSV gerado")
    print("2. Para cada vídeo, leia 'description_preview'")
    print("3. Preencha as colunas:")
    print("   - has_spotify_link: 'sim' se contém link do Spotify, 'nao' caso contrário")
    print("   - has_spotify_text: 'sim' se menciona Spotify por texto, 'nao' caso contrário")
    print("   - manual_call2go_type: 'link_direto', 'texto_implicito' ou 'nenhum'")
    print("   - manual_channel_call2go_type: 'link_direto', 'texto_implicito' ou 'nenhum'")
    print("   - notes: qualquer observação relevante")
    print("4. Salve o arquivo como 'data/validation/ground_truth.csv'")
    print("\nEssa anotação será usada como referência para medir a acurácia do detector.")


if __name__ == "__main__":
    generate_validation_sample()
