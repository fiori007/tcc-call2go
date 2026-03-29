import os
import json
import re
import pandas as pd

def detect_call2go(text):
    """
    Analisa o texto via Expressões Regulares para detectar a estratégia Call2Go.
    Retorna: (has_call2go, call_type)
    """
    if not isinstance(text, str):
        return 0, 'nenhum'
    
    # Padroniza o texto para minúsculas para facilitar o matching
    text_lower = text.lower()
    
    # 1. Busca por Link Direto (Spoti.fi, sptfy.com ou open.spotify.com)
    link_pattern = r'(https?://(?:open\.spotify\.com|spoti\.fi|sptfy\.com)[^\s]+)'
    if re.search(link_pattern, text_lower):
        return 1, 'link_direto'
        
    # 2. Busca por Texto Implícito (Semântica)
    # Lista de padrões que indicam direcionamento de plataforma
    implicit_patterns = [
        r'ou[çc]a no spotify',
        r'dispon[ií]vel no spotify',
        r'stream.*spotify',
        r'ouvir.*spotify',
        r'\bspotify\b'  # Captura apenas a palavra isolada como fallback
    ]
    
    for pattern in implicit_patterns:
        if re.search(pattern, text_lower):
            return 1, 'texto_implicito'
            
    return 0, 'nenhum'


def detect_call2go_channel(channel_description):
    """
    Analisa a descrição do PERFIL DO CANAL do YouTube.
    Detecta se o artista coloca link/referência ao Spotify na bio do canal.
    Retorna: (has_call2go_channel, channel_call2go_type)
    """
    if not isinstance(channel_description, str) or not channel_description.strip():
        return 0, 'nenhum'

    text_lower = channel_description.lower()

    # Link direto na bio do canal (spoti.fi, sptfy.com ou open.spotify.com)
    link_pattern = r'(https?://(?:open\.spotify\.com|spoti\.fi|sptfy\.com)[^\s]+)'
    if re.search(link_pattern, text_lower):
        return 1, 'link_direto'

    # Texto implícito na bio do canal
    implicit_patterns = [
        r'ou[çc]a no spotify',
        r'dispon[ií]vel no spotify',
        r'stream.*spotify',
        r'ouvir.*spotify',
        r'\bspotify\b',
    ]

    for pattern in implicit_patterns:
        if re.search(pattern, text_lower):
            return 1, 'texto_implicito'

    return 0, 'nenhum'

def process_videos():
    print("Iniciando Pipeline de Detecção NLP para Call2Go...")
    
    # Caminhos relativos à raiz do projeto
    input_file = "data/raw/youtube_videos_raw.jsonl"
    output_file = "data/processed/youtube_call2go_flagged.csv"
    
    if not os.path.exists(input_file):
        print(f"[ERRO] Arquivo bruto não encontrado em {input_file}. Rode os coletores primeiro.")
        return
        
    processed_data = []
    
    # Leitura otimizada de JSONL (linha por linha, não sobrecarrega a RAM)
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            video = json.loads(line)
            
            # Nível 1: Detecta Call2Go na descrição do VÍDEO
            has_call2go, call_type = detect_call2go(video.get('description', ''))
            
            # Nível 2: Detecta Call2Go na descrição do PERFIL DO CANAL
            has_channel_call2go, channel_call2go_type = detect_call2go_channel(
                video.get('channel_description', ''))

            # Classificação combinada: vídeo prevalece, canal complementa
            # Se o vídeo já tem Call2Go, mantém. Se não, olha o canal.
            combined_has = has_call2go or has_channel_call2go
            if has_call2go:
                combined_type = call_type
                combined_source = 'video'
            elif has_channel_call2go:
                combined_type = channel_call2go_type
                combined_source = 'canal'
            else:
                combined_type = 'nenhum'
                combined_source = 'nenhum'
            
            # Mapeia as colunas extraindo apenas o necessário para a Análise Estatística
            processed_data.append({
                'video_id': video.get('video_id'),
                'artist_name': video.get('artist_name'),
                'title': video.get('title'),
                'published_at': video.get('published_at'),
                'view_count': video.get('view_count'),
                'like_count': video.get('like_count'),
                'comment_count': video.get('comment_count'),
                'has_call2go': int(combined_has),
                'call2go_type': combined_type,
                'call2go_source': combined_source,
                'video_call2go': call_type,
                'channel_call2go': channel_call2go_type,
            })
            
    # Converte para DataFrame do Pandas para sumarização e exportação
    df = pd.DataFrame(processed_data)
    
    # Garante que a pasta de destino exista
    os.makedirs("data/processed", exist_ok=True)
    
    # Salva o dataset limpo e enriquecido
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"✅ Processamento concluído. {len(df)} vídeos analisados.")

    # Resumo por tipo combinado
    print(f"\n--- DISTRIBUIÇÃO COMBINADA (Vídeo + Canal) ---")
    for ctype, count in df['call2go_type'].value_counts().items():
        pct = count / len(df) * 100
        print(f"  {ctype}: {count} ({pct:.1f}%)")

    # Resumo por fonte
    print(f"\n--- FONTE DA DETECÇÃO ---")
    for source, count in df['call2go_source'].value_counts().items():
        pct = count / len(df) * 100
        print(f"  {source}: {count} ({pct:.1f}%)")

    return df


if __name__ == "__main__":
    process_videos()