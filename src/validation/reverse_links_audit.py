"""
Auditoria automatizada de links de volta cross-platform (67 artistas).

Escopo:
- Spotify -> YouTube
- Spotify -> Last.fm
- Last.fm -> YouTube
- Last.fm -> Spotify

Estratégia:
- Spotify: pagina renderizada (Playwright), coleta links externos do perfil.
- Last.fm: pagina renderizada (Playwright), coleta links da secao "External Links".

Saida:
- data/validation/cross_platform_reverse_links_audit.csv
- data/validation/cross_platform_reverse_links_summary.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import pandas as pd
from playwright.sync_api import BrowserContext, Page, TimeoutError, sync_playwright


YOUTUBE_DOMAINS = ("youtube.com", "youtu.be")
LASTFM_DOMAINS = ("last.fm",)
SPOTIFY_DOMAINS = ("open.spotify.com", "spoti.fi", "sptfy.com", "spotify.com")

DEFAULT_SEED = "data/seed/artistas.csv"
DEFAULT_LASTFM = "data/raw/lastfm_artists_2026-04-18.csv"
DEFAULT_OUT_CSV = "data/validation/cross_platform_reverse_links_audit.csv"
DEFAULT_OUT_JSON = "data/validation/cross_platform_reverse_links_summary.json"


def _normalize_url(url: str) -> str:
    if not isinstance(url, str):
        return ""
    return url.strip().rstrip("/ ")


def _contains_domain(url: str, domains: Tuple[str, ...]) -> bool:
    u = _normalize_url(url).lower()
    return any(d in u for d in domains)


def _dedupe_keep_order(values: List[str]) -> List[str]:
    seen = set()
    output = []
    for v in values:
        nv = _normalize_url(v)
        if not nv:
            continue
        if nv not in seen:
            seen.add(nv)
            output.append(nv)
    return output


def _load_artists(seed_path: str, lastfm_path: str) -> pd.DataFrame:
    seed = pd.read_csv(seed_path, usecols=["artist_name", "spotify_id"])
    lastfm = pd.read_csv(lastfm_path, usecols=["artist_name", "lastfm_url"])

    merged = seed.merge(lastfm, on="artist_name", how="left")
    merged["spotify_id"] = merged["spotify_id"].fillna("").astype(str)
    merged["lastfm_url"] = merged["lastfm_url"].fillna("").astype(str)
    return merged


def _goto_with_retry(page: Page, url: str, retries: int = 3) -> Tuple[bool, str]:
    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            # Pequeno settle para elementos renderizados atrasados.
            page.wait_for_timeout(1200)
            return True, ""
        except TimeoutError as exc:
            last_err = f"timeout: {exc}"
        except Exception as exc:  # noqa: BLE001
            last_err = f"goto_error: {exc}"

        backoff_ms = 700 * attempt
        page.wait_for_timeout(backoff_ms)

    return False, last_err


def _extract_spotify_external_links(page: Page) -> List[str]:
    js = r"""
    () => {
      const anchors = Array.from(document.querySelectorAll('a[href]'));
      const hrefs = anchors
        .map(a => a.href)
        .filter(h => typeof h === 'string' && h.startsWith('http'));
      return [...new Set(hrefs)];
    }
    """
    links = page.evaluate(js)
    if not isinstance(links, list):
        return []

    # Filtra links claramente internos da navegacao do Spotify.
    output = []
    for link in links:
        ll = _normalize_url(str(link)).lower()
        if not ll:
            continue
        if ll.startswith("https://open.spotify.com/"):
            continue
        if "spotify.com/br" in ll or "spotify.com/pt" in ll:
            continue
        output.append(str(link))

    return _dedupe_keep_order(output)


def _extract_lastfm_external_links(page: Page) -> List[str]:
    # Tenta capturar somente links da secao com titulo "External Links".
    js = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
      const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,dt,span,div'))
        .filter(el => norm(el.textContent) === 'external links');

      const collectHrefs = (root) => {
        if (!root) return [];
        return Array.from(root.querySelectorAll('a[href]'))
          .map(a => a.href)
          .filter(h => typeof h === 'string' && h.startsWith('http'));
      };

      for (const h of headings) {
        const primary = h.closest('section,aside,div,dl') || h.parentElement;
        let hrefs = collectHrefs(primary);

        if (!hrefs.length && primary) {
          let sib = primary.nextElementSibling;
          let guard = 0;
          while (sib && guard < 3) {
            hrefs = hrefs.concat(collectHrefs(sib));
            sib = sib.nextElementSibling;
            guard += 1;
          }
        }

        if (hrefs.length) {
          return [...new Set(hrefs)];
        }
      }

      return [];
    }
    """

    links = page.evaluate(js)
    if not isinstance(links, list):
        return []
    return _dedupe_keep_order([str(x) for x in links])


def _build_context(playwright_obj, headless: bool) -> BrowserContext:
    browser = playwright_obj.chromium.launch(headless=headless)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
    )
    return context


def _audit_spotify(page: Page, spotify_id: str) -> Dict[str, object]:
    result = {
        "status_spotify": "skipped",
        "error_spotify": "",
        "spotify_links": [],
        "sp_to_yt": 0,
        "sp_to_lfm": 0,
    }

    spotify_id = (spotify_id or "").strip()
    if not spotify_id:
        result["error_spotify"] = "missing_spotify_id"
        return result

    url = f"https://open.spotify.com/artist/{spotify_id}"
    ok, err = _goto_with_retry(page, url, retries=3)
    if not ok:
        result["status_spotify"] = "error"
        result["error_spotify"] = err
        return result

    links = _extract_spotify_external_links(page)
    result["spotify_links"] = links
    result["status_spotify"] = "ok"
    result["sp_to_yt"] = int(
        any(_contains_domain(x, YOUTUBE_DOMAINS) for x in links))
    result["sp_to_lfm"] = int(
        any(_contains_domain(x, LASTFM_DOMAINS) for x in links))
    return result


def _audit_lastfm(page: Page, lastfm_url: str) -> Dict[str, object]:
    result = {
        "status_lastfm": "skipped",
        "error_lastfm": "",
        "lastfm_external_links": [],
        "lfm_to_yt": 0,
        "lfm_to_sp": 0,
    }

    lastfm_url = (lastfm_url or "").strip()
    if not lastfm_url:
        result["error_lastfm"] = "missing_lastfm_url"
        return result

    ok, err = _goto_with_retry(page, lastfm_url, retries=3)
    if not ok:
        result["status_lastfm"] = "error"
        result["error_lastfm"] = err
        return result

    links = _extract_lastfm_external_links(page)
    result["lastfm_external_links"] = links
    result["status_lastfm"] = "ok"
    result["lfm_to_yt"] = int(
        any(_contains_domain(x, YOUTUBE_DOMAINS) for x in links))
    result["lfm_to_sp"] = int(
        any(_contains_domain(x, SPOTIFY_DOMAINS) for x in links))

    # Se a secao nao apareceu, registra como avisado para auditoria.
    if not links:
        result["status_lastfm"] = "selector_missing"

    return result


def run_audit(
    seed_path: str,
    lastfm_path: str,
    out_csv: str,
    out_json: str,
    headless: bool,
    limit: int | None,
) -> None:
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)

    artists = _load_artists(seed_path, lastfm_path)
    if limit is not None and limit > 0:
        artists = artists.head(limit).copy()

    rows = []

    started_at = datetime.now(timezone.utc)
    with sync_playwright() as p:
        context = _build_context(p, headless=headless)
        page_sp = context.new_page()
        page_lfm = context.new_page()

        for idx, row in artists.iterrows():
            artist_name = row["artist_name"]
            spotify_id = row["spotify_id"]
            lastfm_url = row["lastfm_url"]

            sp_res = _audit_spotify(page_sp, spotify_id)
            lfm_res = _audit_lastfm(page_lfm, lastfm_url)

            rows.append(
                {
                    "artist_name": artist_name,
                    "spotify_id": spotify_id,
                    "lastfm_url": lastfm_url,
                    "status_spotify": sp_res["status_spotify"],
                    "error_spotify": sp_res["error_spotify"],
                    "spotify_links": " | ".join(sp_res["spotify_links"]),
                    "sp_to_yt": sp_res["sp_to_yt"],
                    "sp_to_lfm": sp_res["sp_to_lfm"],
                    "status_lastfm": lfm_res["status_lastfm"],
                    "error_lastfm": lfm_res["error_lastfm"],
                    "lastfm_external_links": " | ".join(lfm_res["lastfm_external_links"]),
                    "lfm_to_yt": lfm_res["lfm_to_yt"],
                    "lfm_to_sp": lfm_res["lfm_to_sp"],
                    "audit_ts_utc": datetime.now(timezone.utc).isoformat(),
                }
            )

            if ((idx + 1) % 10) == 0:
                print(
                    f"[progress] {idx + 1}/{len(artists)} artistas auditados")

        context.close()

    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False, encoding="utf-8")

    ok_spotify = int((df["status_spotify"] == "ok").sum())
    ok_lastfm = int(df["status_lastfm"].isin(["ok", "selector_missing"]).sum())

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "started_at_utc": started_at.isoformat(),
        "n_artists": int(len(df)),
        "coverage": {
            "spotify_checked_ok": ok_spotify,
            "spotify_checked_total": int(len(df)),
            "lastfm_checked_ok_or_selector_missing": ok_lastfm,
            "lastfm_checked_total": int(len(df)),
        },
        "directions": {
            "spotify_to_youtube": {
                "count": int(df["sp_to_yt"].sum()),
                "artists": df.loc[df["sp_to_yt"] == 1, "artist_name"].tolist(),
            },
            "spotify_to_lastfm": {
                "count": int(df["sp_to_lfm"].sum()),
                "artists": df.loc[df["sp_to_lfm"] == 1, "artist_name"].tolist(),
            },
            "lastfm_to_youtube": {
                "count": int(df["lfm_to_yt"].sum()),
                "artists": df.loc[df["lfm_to_yt"] == 1, "artist_name"].tolist(),
            },
            "lastfm_to_spotify": {
                "count": int(df["lfm_to_sp"].sum()),
                "artists": df.loc[df["lfm_to_sp"] == 1, "artist_name"].tolist(),
            },
        },
        "errors": {
            "spotify_errors": int((df["status_spotify"] == "error").sum()),
            "lastfm_errors": int((df["status_lastfm"] == "error").sum()),
            "spotify_error_artists": df.loc[df["status_spotify"] == "error", "artist_name"].tolist(),
            "lastfm_error_artists": df.loc[df["status_lastfm"] == "error", "artist_name"].tolist(),
        },
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n[OK] Auditoria concluida")
    print(f"[OK] CSV: {out_csv}")
    print(f"[OK] JSON: {out_json}")
    print("\nResumo:")
    print(
        f"  Spotify->YouTube: {summary['directions']['spotify_to_youtube']['count']}"
    )
    print(
        f"  Spotify->Last.fm: {summary['directions']['spotify_to_lastfm']['count']}"
    )
    print(
        f"  Last.fm->YouTube: {summary['directions']['lastfm_to_youtube']['count']}"
    )
    print(
        f"  Last.fm->Spotify: {summary['directions']['lastfm_to_spotify']['count']}"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audita links de volta cross-platform para artistas do seed."
    )
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--lastfm", default=DEFAULT_LASTFM)
    parser.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    parser.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    parser.add_argument("--headful", action="store_true",
                        help="Abre browser visivel")
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_audit(
        seed_path=args.seed,
        lastfm_path=args.lastfm,
        out_csv=args.out_csv,
        out_json=args.out_json,
        headless=not args.headful,
        limit=args.limit,
    )
