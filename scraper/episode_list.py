# scraper/episode_list.py
# -*- coding: utf-8 -*-

import json
import re

from scraper.fetch import fetch_html
from utils.storage import load_json, save_json
from utils.sanitizer import sanitize_html
from ia.analyzer import analyze_and_update_rules

BASE = "https://goyabu.io"
RULES_PATH = "rules/goyabu.json"


def detect_is_movie(html, rules):
    key = rules.get("episode_js_key", "allEpisodes")

    try:
        match = re.search(
            rf"{key}\s*=\s*(\[[\s\S]*?\])\s*;",
            html
        )
        if not match:
            return False

        data = json.loads(match.group(1))
        return isinstance(data, list) and len(data) == 1

    except Exception:
        return False


def get_episodes(anime_url):
    rules = load_json(RULES_PATH, default={})
    html = fetch_html(anime_url)

    if not html:
        return []

    # 🎬 Filme
    if detect_is_movie(html, rules):
        return [{
            "episode": "1",
            "url": anime_url,
            "type": "movie"
        }]

    key = rules.get("episode_js_key", "allEpisodes")

    match = re.search(
        rf"{key}\s*=\s*(\[[\s\S]*?\])\s*;",
        html
    )

    if not match:
        print("[EPISODES] Não encontrado → acionando IA")
        old_rules = load_json(RULES_PATH, default={})

        clean_html = sanitize_html(html)
        ok = analyze_and_update_rules(clean_html, "episode_list")

        if ok:
            rules = load_json(RULES_PATH, default={})
            key = rules.get("episode_js_key", "allEpisodes")
            match = re.search(
                rf"{key}\s*=\s*(\[[\s\S]*?\])\s*;",
                html
            )

        if not match:
            print("[EPISODES] IA falhou → rollback")
            save_json(RULES_PATH, old_rules)
            return []

    try:
        raw = match.group(1).replace("\\/", "/")
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
