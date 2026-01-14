# scraper/episode_list.py
# -*- coding: utf-8 -*-

import json
import re

from scraper.fetch import fetch_html
from utils.storage import load_json

BASE = "https://goyabu.io"
RULES_PATH = "rules/goyabu.json"


# ======================================
# Detecta se é filme (1 episódio)
# ======================================
def detect_is_movie(html, rules):
    key = rules.get("episode_js_key", "const allEpisodes")

    if key not in html:
        return False

    try:
        match = re.search(
            r"const\s+allEpisodes\s*=\s*(\[[\s\S]*?\])\s*;",
            html
        )
        if not match:
            return False

        episodes = json.loads(match.group(1))
        return isinstance(episodes, list) and len(episodes) == 1

    except Exception:
        return False


# ======================================
# Lista episódios
# ======================================
def get_episodes(anime_url):
    rules = load_json(RULES_PATH)
    html = fetch_html(anime_url)

    # 🎬 Filme
    if detect_is_movie(html, rules):
        return [{
            "episode": "1",
            "url": anime_url,
            "type": "movie"
        }]

    # 📺 Série
    match = re.search(
        r"const\s+allEpisodes\s*=\s*(\[[\s\S]*?\])\s*;",
        html
    )

    if not match:
        return []

    raw = match.group(1)

    try:
        # JS → JSON seguro
        raw = raw.replace("\\/", "/")
        episodes = json.loads(raw)
    except Exception:
        return []

    result = []

    for ep in episodes:
        ep_num = ep.get("episodio") or ep.get("episode")
        ep_id = ep.get("id")

        if not ep_num or not ep_id:
            continue

        result.append({
            "episode": str(ep_num),
            "url": f"{BASE}/{ep_id}",
            "type": "episode"
        })

    return result
