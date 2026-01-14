# scraper/episode_list.py
# -*- coding: utf-8 -*-

import json
import re
from bs4 import BeautifulSoup

from scraper.fetch import fetch_html
from utils.storage import load_json

BASE = "https://goyabu.io"
RULES_PATH = "rules/goyabu.json"


def detect_is_movie(html, rules):
    key = rules.get("episode_js_key", "const allEpisodes")

    if key not in html:
        return False

    try:
        m = re.search(r"const allEpisodes\s*=\s*([\s\S]*?);", html)
        if not m:
            return False

        eps = json.loads(m.group(1).replace("\\/", "/"))
        return isinstance(eps, list) and len(eps) == 1
    except Exception:
        return False


def get_episodes(anime_url):
    rules = load_json(RULES_PATH)
    html = fetch_html(anime_url)

    # 🎬 Filme?
    if detect_is_movie(html, rules):
        return [{
            "episode": 1,
            "url": anime_url,
            "type": "movie"
        }]

    # 📺 Série
    m = re.search(r"const allEpisodes\s*=\s*([\s\S]*?);", html)
    if not m:
        return []

    try:
        episodes = json.loads(m.group(1).replace("\\
