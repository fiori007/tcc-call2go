"""
Auditoria automatizada do detector Call2Go por regra (regex_audit.py).

Percorre o corpus completo (1641 videos) e rastreia qual regra do detector
disparou primeiro para cada video positivo. Gera relatorio de cobertura por
regra e perfil de risco do fallback R5 (\bspotify\b).

Regras auditadas (nivel video):
  R1 -- Link direto (open.spotify.com / spoti.fi / sptfy.com)
  R2 -- Labeled redirect (spotify: https://...)
  R3 -- URL com spotify/sptfy no path (bit.ly/LivinhoNoSpotify etc.)
  R4 -- Texto implicito CTA (ouca/disponivel/stream/ouvir + spotify)
  R5 -- Fallback \\bspotify\\b (mais liberal; maior risco de FP)
  NEG -- Nao detectado (negativo)

Outputs:
  data/validation/regex_audit_report.txt
  data/validation/regex_rule_breakdown.csv
"""

import os
import re
import json
import pandas as pd
from datetime import datetime

# Limiar de alerta para uso do fallback R5
FALLBACK_RISK_THRESHOLD = 0.30  # >30% do total positivos = risco metodologico


# ------------------------------------------------------------------ #
#  Reproduz as regras do detector em sequencia (first-match)          #
#  sem alterar o comportamento de call2go_detector.py                 #
# ------------------------------------------------------------------ #

_NARRATIVE_PATTERNS = [
    r'chart\w*\s+(?:do|no|da|dos|nos)\s+spotify',
    r'ranking\s+(?:do|no|da)\s+spotify',
    r'top\s+\d+\s+(?:do|no)\s+spotify',
    r'milh[ao]\w*\s+(?:de\s+)?(?:plays?|streams?|reprodu[cc][ao])\w*\s+(?:no|do)\s+spotify',
    r'\d+\s+dias?\s+(?:no|nos)\s+chart',
    r'#\d+\s+(?:no|do)\s+spotify',
]


def _is_narrative_mention(text_lower):
    return any(re.search(p, text_lower) for p in _NARRATIVE_PATTERNS)


def _which_rule_fired(text):
    """Retorna qual regra disparou primeiro (first-match) para um texto de descricao.

    Returns:
        str: 'R1' | 'R2' | 'R3' | 'R4' | 'R5' | 'NEG'
    """
    if not isinstance(text, str):
        return 'NEG'

    text_lower = text.lower()

    # R1 -- Link direto (URLs Spotify literais)
    if re.search(r'https?://(?:open\.spotify\.com|spoti\.fi|sptfy\.com)[^\s]+', text_lower):
        return 'R1'

    # R2 -- Labeled redirect (Spotify: https://...)
    if re.search(r'spotify\s*[:\|\-\u2013]\s*https?://[^\s]+', text_lower):
        return 'R2'

    # R3 -- URL com spotify/sptfy no path
    if re.search(r'https?://[^\s]*(?:spotify|sptfy)[^\s]*', text_lower):
        return 'R3'

    # R4 -- Texto implicito CTA
    implicit_patterns = [
        r'ou[cc]a\b.{0,50}\bspotify',
        r'dispon[ii]vel\b.{0,30}\bspotify',
        r'\bstream\b.{0,50}\bspotify',
        r'\bouvir\b.{0,50}\bspotify',
    ]
    for pattern in implicit_patterns:
        if re.search(pattern, text_lower):
            return 'R4'

    # R5 -- Fallback \bspotify\b (guardado por narrativa)
    if re.search(r'\bspotify\b', text_lower) and not _is_narrative_mention(text_lower):
        return 'R5'

    return 'NEG'


# ------------------------------------------------------------------ #
#  Funcao principal de auditoria                                       #
# ------------------------------------------------------------------ #

def run_regex_audit(
    flagged_csv="data/processed/youtube_call2go_flagged.csv",
    raw_jsonl="data/raw/youtube_videos_raw.jsonl",
    report_txt="data/validation/regex_audit_report.txt",
    breakdown_csv="data/validation/regex_rule_breakdown.csv",
):
    """
    Audita o detector Call2Go regra por regra sobre o corpus completo.

    Carrega as descricoes brutas do JSONL e re-executa as regras em
    sequencia (first-match), registrando qual regra disparou para cada
    video positivo.

    Args:
        flagged_csv: CSV com resultado final do detector (has_call2go_video).
        raw_jsonl: JSONL com videos brutos (para obter descricao original).
        report_txt: Caminho do relatorio texto gerado.
        breakdown_csv: Caminho do CSV com breakdown por regra e artista.
    """
    os.makedirs("data/validation", exist_ok=True)

    print("=" * 60)
    print("AUDITORIA DE REGRAS REGEX -- DETECTOR CALL2GO")
    print("=" * 60)

    # ------------------------------------------------------------------ #
    # 1. Carrega descricoes brutas do JSONL                               #
    # ------------------------------------------------------------------ #
    if not os.path.exists(raw_jsonl):
        print(f"[ERRO] JSONL nao encontrado: {raw_jsonl}")
        return

    desc_map = {}  # video_id -> description
    with open(raw_jsonl, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                vid = obj.get('video_id') or obj.get('id')
                desc = obj.get('description', '')
                if vid:
                    desc_map[vid] = desc
            except json.JSONDecodeError:
                pass

    print(f"  Videos no JSONL: {len(desc_map)}")

    # ------------------------------------------------------------------ #
    # 2. Carrega CSV com flags do detector                                #
    # ------------------------------------------------------------------ #
    if not os.path.exists(flagged_csv):
        print(f"[ERRO] CSV flagged nao encontrado: {flagged_csv}")
        return

    df = pd.read_csv(flagged_csv)
    print(f"  Videos no CSV flagged: {len(df)}")

    # Mapeia video_id para artist_name
    video_id_col = 'video_id' if 'video_id' in df.columns else 'id'
    artist_col = 'artist_name' if 'artist_name' in df.columns else None

    # ------------------------------------------------------------------ #
    # 3. Aplica auditoria de regra a cada video                           #
    # ------------------------------------------------------------------ #
    rows = []
    for _, row in df.iterrows():
        vid = str(row.get(video_id_col, ''))
        desc = desc_map.get(vid, row.get('description', ''))
        artist = row.get(artist_col, 'DESCONHECIDO') if artist_col else 'DESCONHECIDO'
        rule = _which_rule_fired(desc)

        # Flag do detector original (usado para comparar com auditoria)
        has_video = int(row.get('has_call2go_video', row.get('has_call2go', 0)))

        rows.append({
            'video_id': vid,
            'artist_name': artist,
            'rule_fired': rule,
            'has_call2go_video_original': has_video,
            'description_snippet': str(desc)[:120].replace('\n', ' '),
        })

    df_audit = pd.DataFrame(rows)

    # ------------------------------------------------------------------ #
    # 4. Estatisticas por regra                                           #
    # ------------------------------------------------------------------ #
    total_videos = len(df_audit)
    total_positivos_original = df_audit['has_call2go_video_original'].sum()
    total_positivos_audit = (df_audit['rule_fired'] != 'NEG').sum()

    rule_counts = df_audit['rule_fired'].value_counts()
    positivos_audit = df_audit[df_audit['rule_fired'] != 'NEG']

    # Percentual do total de positivos (auditoria)
    rule_pct = (rule_counts / total_positivos_audit * 100).round(1)

    # Percentual do corpus total
    rule_pct_total = (rule_counts / total_videos * 100).round(2)

    # Risco do fallback
    n_r5 = rule_counts.get('R5', 0)
    fallback_pct = n_r5 / total_positivos_audit if total_positivos_audit > 0 else 0
    fallback_risk = fallback_pct > FALLBACK_RISK_THRESHOLD

    # ------------------------------------------------------------------ #
    # 5. Breakdown por artista                                            #
    # ------------------------------------------------------------------ #
    artist_stats = (
        df_audit.groupby('artist_name')['rule_fired']
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )
    for rule in ['R1', 'R2', 'R3', 'R4', 'R5', 'NEG']:
        if rule not in artist_stats.columns:
            artist_stats[rule] = 0

    artist_stats['total_videos'] = artist_stats[['R1', 'R2', 'R3', 'R4', 'R5', 'NEG']].sum(axis=1)
    artist_stats['total_positivos'] = artist_stats[['R1', 'R2', 'R3', 'R4', 'R5']].sum(axis=1)
    artist_stats['call2go_rate'] = (
        artist_stats['total_positivos'] / artist_stats['total_videos'] * 100
    ).round(1)
    artist_stats['r5_only'] = artist_stats['R5']
    artist_stats['r5_pct_of_positive'] = (
        artist_stats['R5'] / artist_stats['total_positivos'].replace(0, float('nan')) * 100
    ).fillna(0).round(1)

    # Exemplos do fallback R5
    r5_examples = df_audit[df_audit['rule_fired'] == 'R5'].head(10)

    # ------------------------------------------------------------------ #
    # 6. Salva CSV de breakdown                                           #
    # ------------------------------------------------------------------ #
    df_audit.to_csv(breakdown_csv, index=False, encoding='utf-8-sig')
    print(f"\n  [OK] Breakdown CSV: {breakdown_csv}")

    # ------------------------------------------------------------------ #
    # 7. Gera relatorio texto                                             #
    # ------------------------------------------------------------------ #
    lines = []
    lines.append("=" * 60)
    lines.append("AUDITORIA DE REGRAS REGEX -- DETECTOR CALL2GO")
    lines.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Total de videos no corpus:     {total_videos}")
    lines.append(f"Positivos (detector original): {total_positivos_original}")
    lines.append(f"Positivos (auditoria regras):  {total_positivos_audit}")
    lines.append(f"Negativos (auditoria regras):  {total_videos - total_positivos_audit}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("BREAKDOWN POR REGRA (% do total de positivos na auditoria)")
    lines.append("-" * 60)

    for rule in ['R1', 'R2', 'R3', 'R4', 'R5']:
        n = rule_counts.get(rule, 0)
        pct_pos = rule_pct.get(rule, 0)
        pct_tot = rule_pct_total.get(rule, 0)
        desc = {
            'R1': 'Link direto (open.spotify.com / spoti.fi / sptfy.com)',
            'R2': 'Labeled redirect (spotify: https://...)',
            'R3': 'URL com spotify/sptfy no path (bit.ly etc.)',
            'R4': 'Texto implicito CTA (ouca/disponivel/stream/ouvir)',
            'R5': 'Fallback \\bspotify\\b [RISCO MAIS ALTO DE FP]',
        }[rule]
        lines.append(f"  {rule}  {n:4d} videos ({pct_pos:5.1f}% positivos | {pct_tot:4.2f}% corpus)  -- {desc}")

    lines.append(f"  NEG  {rule_counts.get('NEG', total_videos - total_positivos_audit):4d} videos -- Nao detectado")
    lines.append("")
    lines.append("-" * 60)
    lines.append(f"PERFIL DE RISCO DO FALLBACK R5")
    lines.append("-" * 60)
    lines.append(f"  Videos R5 / total positivos: {n_r5}/{total_positivos_audit} = {fallback_pct*100:.1f}%")
    if fallback_risk:
        lines.append(f"  [ALERTA] R5 > {FALLBACK_RISK_THRESHOLD*100:.0f}% dos positivos -- RISCO METODOLOGICO ELEVADO")
        lines.append("  Considerar auditoria manual dos casos R5 antes de publicar resultados.")
    else:
        lines.append(f"  [OK] R5 dentro do limiar aceito (threshold = {FALLBACK_RISK_THRESHOLD*100:.0f}%)")

    lines.append("")
    lines.append("-" * 60)
    lines.append("PRIMEIROS 10 EXEMPLOS DE DETECCAO SOMENTE POR R5 (FALLBACK)")
    lines.append("-" * 60)
    if r5_examples.empty:
        lines.append("  Nenhum exemplo R5 encontrado.")
    else:
        for _, ex in r5_examples.iterrows():
            lines.append(f"  [{ex['artist_name']}] {ex['video_id']}")
            lines.append(f"    Descricao: {ex['description_snippet']}")

    lines.append("")
    lines.append("-" * 60)
    lines.append("TOP 10 ARTISTAS COM MAIOR TAXA DE CALL2GO")
    lines.append("-" * 60)
    top10 = artist_stats.sort_values('call2go_rate', ascending=False).head(10)
    for _, ar in top10.iterrows():
        lines.append(
            f"  {ar['artist_name']:<30} {ar['call2go_rate']:5.1f}%  "
            f"(R1={ar['R1']} R2={ar['R2']} R3={ar['R3']} R4={ar['R4']} R5={ar['R5']})"
        )

    lines.append("")
    lines.append("-" * 60)
    lines.append("ARTISTAS COM R5 > 50% DOS PROPRIOS POSITIVOS (alto risco individual)")
    lines.append("-" * 60)
    high_r5 = artist_stats[
        (artist_stats['total_positivos'] > 0) &
        (artist_stats['r5_pct_of_positive'] > 50)
    ].sort_values('r5_pct_of_positive', ascending=False)
    if high_r5.empty:
        lines.append("  Nenhum artista com risco R5 elevado individual.")
    else:
        for _, ar in high_r5.iterrows():
            lines.append(
                f"  {ar['artist_name']:<30} R5={ar['r5_pct_of_positive']:.0f}% "
                f"({ar['R5']}/{ar['total_positivos']} positivos)"
            )

    lines.append("")
    lines.append("=" * 60)
    report_text = "\n".join(lines)

    with open(report_txt, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"  [OK] Relatorio: {report_txt}")
    print()
    print(report_text)


if __name__ == "__main__":
    run_regex_audit()
