# scraper/anime_list.py
# -*- coding: utf-8 -*-

from urllib.parse import urljoin
from bs4 import BeautifulSoup

from scraper.fetch import fetch_html
from utils.storage import load_json


BASE = "https://goyabu.io"
RULES_PATH = "rules/goyabu.json"


def get_anime_list(page=1):
    rules = load_json(RULES_PATH)

    url = f"{BASE}/lista-de-animes/page/{page}?l=todos&pg={page}"
    html = fetch_html(url)

    soup = BeautifulSoup(html, "html.parser")

    card_selector = rules.get("anime_card", "article")
    link_selector = rules.get("anime_link", "a[href]")

    animes = []

    for card in soup.select(card_selector):
        a = card.select_one(link_selector)
        if not a:
            continue

        name = a.get_text(" ", strip=True)
        link = urljoin(BASE, a["href"])

        animes.append({
            "name": name,
            "url": link
        })

    return animes
