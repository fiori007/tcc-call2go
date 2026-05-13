"""Coletor complementar para artistas Top-K sem videos coletados.

Identifica artistas que estao no Top-K do Rank Fusion mas nao tem videos no
youtube_call2go_flagged.csv (porque a v1 nao os incluia no seed). Para cada
um, busca o canal pelo nome via YouTube Data API e coleta 30 videos.

Custo aproximado por artista: ~105 unidades (100 search + ~5 coleta).
Para 20 artistas: ~2.100 unidades de quota (21% da quota diaria de 10k).

Resume-friendly: salva progresso em data/raw/topk_expansion_progress.json
e retoma da onde parou em caso de interrupcao.
Audit-friendly: nomes ambiguos sao logados em
data/raw/topk_expansion_pending_review.csv para verificacao manual.
"""

import os
import json
import logging
from datetime import datetime, timezone

import pandas as pd
from googleapiclient.errors import HttpError

from src.collectors.youtube_collector import (
    get_youtube_client,
    get_channel_id_by_name,
    get_channel_about,
    get_channel_videos,
    get_video_details,
)
from src.analytics._universe import _normalize_name


logger = logging.getLogger(__name__)


_FUSION_CSV = "data/processed/ranking_fusion_scores.csv"
_FLAGGED_CSV = "data/processed/youtube_call2go_flagged.csv"
_RAW_JSONL = "data/raw/youtube_videos_raw.jsonl"
_PROGRESS_JSON = "data/raw/topk_expansion_progress.json"
_PENDING_CSV = "data/raw/topk_expansion_pending_review.csv"

# Heuristicas de validacao do canal encontrado
_MIN_SUBSCRIBERS_HINT = 1000  # threshold conservador
_MAX_VIDEOS_PER_ARTIST = 30


def _identify_missing_topk_artists() -> pd.DataFrame:
    """Lista artistas Top-K que nao tem videos coletados ainda."""
    if not os.path.exists(_FUSION_CSV):
        raise FileNotFoundError(f"{_FUSION_CSV} nao existe -- rode step 14 antes")

    df_fusion = pd.read_csv(_FUSION_CSV)
    topk = df_fusion[df_fusion['in_top_k'] == True].copy()

    if os.path.exists(_FLAGGED_CSV):
        df_flagged = pd.read_csv(_FLAGGED_CSV)
        artists_with_videos = set(
            df_flagged['artist_name'].apply(_normalize_name).unique())
    else:
        artists_with_videos = set()

    topk['has_videos'] = topk['artist_normalized'].isin(artists_with_videos)
    missing = topk[~topk['has_videos']].copy()
    missing = missing.sort_values('score_combined', ascending=False)
    return missing


def _load_progress() -> dict:
    if not os.path.exists(_PROGRESS_JSON):
        return {'completed': [], 'failed': [], 'pending_review': []}
    with open(_PROGRESS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_progress(progress: dict):
    os.makedirs(os.path.dirname(_PROGRESS_JSON), exist_ok=True)
    with open(_PROGRESS_JSON, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def _resolve_channel(youtube, artist_name: str) -> dict:
    """Busca canal por nome e retorna metadados para validacao manual.

    Returns:
        {
            'found': bool,
            'channel_id': str | None,
            'channel_title': str,
            'subscriber_count': int,
            'video_count': int,
            'description_preview': str (primeiros 100 chars),
            'reason': 'ok' | 'low_subs' | 'not_found' | 'api_error',
        }
    """
    try:
        channel_id = get_channel_id_by_name(youtube, artist_name)
    except ValueError:
        return {'found': False, 'channel_id': None, 'reason': 'not_found',
                'channel_title': '', 'subscriber_count': 0,
                'video_count': 0, 'description_preview': ''}
    except HttpError as e:
        logger.error("API error buscando %s: %s", artist_name, e)
        return {'found': False, 'channel_id': None, 'reason': 'api_error',
                'channel_title': '', 'subscriber_count': 0,
                'video_count': 0, 'description_preview': ''}

    # Inspeciona o canal encontrado para validacao
    try:
        res = youtube.channels().list(
            id=channel_id, part='snippet,statistics').execute()
    except Exception as e:
        logger.warning("channels.list falhou para %s: %s", channel_id, e)
        return {'found': True, 'channel_id': channel_id, 'reason': 'no_metadata',
                'channel_title': '', 'subscriber_count': 0,
                'video_count': 0, 'description_preview': ''}

    if not res.get('items'):
        return {'found': False, 'channel_id': None, 'reason': 'channel_deleted',
                'channel_title': '', 'subscriber_count': 0,
                'video_count': 0, 'description_preview': ''}

    item = res['items'][0]
    snippet = item.get('snippet', {})
    stats = item.get('statistics', {})

    subs = int(stats.get('subscriberCount', 0))
    title = snippet.get('title', '')
    desc = snippet.get('description', '') or ''
    reason = 'ok' if subs >= _MIN_SUBSCRIBERS_HINT else 'low_subs'

    return {
        'found': True,
        'channel_id': channel_id,
        'channel_title': title,
        'subscriber_count': subs,
        'video_count': int(stats.get('videoCount', 0)),
        'description_preview': desc[:100],
        'reason': reason,
    }


def _collect_artist(youtube, artist_norm: str, artist_display: str):
    """Coleta canal + videos + about para um unico artista. Retorna lista de
    dicts pronta para apender em youtube_videos_raw.jsonl."""
    info = _resolve_channel(youtube, artist_display)
    if not info['found'] or info['channel_id'] is None:
        return [], info

    channel_id = info['channel_id']
    about = get_channel_about(youtube, channel_id)

    video_ids = get_channel_videos(
        youtube, channel_id, max_results=_MAX_VIDEOS_PER_ARTIST)
    if not video_ids:
        return [], {**info, 'reason': 'no_videos'}

    videos = get_video_details(youtube, video_ids)
    enriched = []
    for v in videos:
        v['artist_name'] = artist_display
        v['channel_description'] = about['channel_description']
        v['channel_keywords'] = about['channel_keywords']
        enriched.append(v)
    return enriched, info


def _append_jsonl(path: str, records: list):
    if not records:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def collect_topk_expansion():
    """Roda a coleta dos artistas Top-K faltantes."""
    print("=" * 60)
    print("TOP-K EXPANSION COLLECTOR")
    print("=" * 60)

    missing = _identify_missing_topk_artists()
    print(f"  Artistas Top-K sem videos: {len(missing)}")

    if missing.empty:
        print("  Nada a coletar -- cobertura ja completa.")
        return

    progress = _load_progress()
    already_done = set(progress.get('completed', []))
    print(f"  Ja completos (resume): {len(already_done)}")

    youtube = get_youtube_client()
    pending_review_rows = []
    new_videos_total = 0

    for idx, row in missing.iterrows():
        artist_norm = row['artist_normalized']
        # Display name: se tem artist_name_seed usa ele, senao usa normalizado
        artist_display = row.get('artist_name_seed') if pd.notna(
            row.get('artist_name_seed')) else artist_norm

        if artist_norm in already_done:
            print(f"\n  [SKIP] {artist_display} (ja coletado)")
            continue

        print(f"\n  [{idx+1}] Coletando: {artist_display}")
        try:
            videos, info = _collect_artist(youtube, artist_norm, artist_display)
        except HttpError as e:
            if e.resp.status in (403, 429):
                print(f"  [QUOTA] esgotada apos {len(already_done)} artistas")
                progress['quota_exceeded_at'] = datetime.now(
                    timezone.utc).isoformat()
                _save_progress(progress)
                return
            logger.error("Erro coletando %s: %s", artist_display, e)
            progress['failed'].append({'artist': artist_norm, 'error': str(e)})
            _save_progress(progress)
            continue
        except Exception as e:
            logger.exception("Erro inesperado em %s", artist_display)
            progress['failed'].append({'artist': artist_norm, 'error': str(e)})
            _save_progress(progress)
            continue

        if not videos:
            print(f"  [VAZIO] reason={info.get('reason')}")
            pending_review_rows.append({
                'artist_normalized': artist_norm,
                'artist_display': artist_display,
                'channel_id': info.get('channel_id'),
                'channel_title': info.get('channel_title', ''),
                'subscriber_count': info.get('subscriber_count', 0),
                'reason': info.get('reason'),
                'description_preview': info.get('description_preview', ''),
            })
            progress['pending_review'].append(artist_norm)
            _save_progress(progress)
            continue

        # Audita canais com poucos inscritos (possivel homonimo)
        if info.get('reason') == 'low_subs':
            pending_review_rows.append({
                'artist_normalized': artist_norm,
                'artist_display': artist_display,
                'channel_id': info.get('channel_id'),
                'channel_title': info.get('channel_title', ''),
                'subscriber_count': info.get('subscriber_count', 0),
                'reason': 'low_subs',
                'description_preview': info.get('description_preview', ''),
            })
            print(f"  [REVIEW] subs={info['subscriber_count']} title={info['channel_title']!r}")

        _append_jsonl(_RAW_JSONL, videos)
        new_videos_total += len(videos)
        progress['completed'].append(artist_norm)
        _save_progress(progress)
        print(f"  [OK] {len(videos)} videos | canal {info.get('channel_title', '?')!r}"
              f" | subs {info.get('subscriber_count', 0):,}")

    # Salva CSV de pending review
    if pending_review_rows:
        os.makedirs(os.path.dirname(_PENDING_CSV), exist_ok=True)
        pd.DataFrame(pending_review_rows).to_csv(
            _PENDING_CSV, index=False, encoding='utf-8')
        print(f"\n  [REVIEW] {len(pending_review_rows)} artistas em {_PENDING_CSV}")

    print(f"\n[OK] Coleta concluida: {new_videos_total} videos novos apendados em {_RAW_JSONL}")
    print(f"     Completos: {len(progress['completed'])} | Pending review: "
          f"{len(progress.get('pending_review', []))} | Falhas: {len(progress.get('failed', []))}")


if __name__ == "__main__":
    collect_topk_expansion()
