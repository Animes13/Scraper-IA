# scraper/anime_list.py
# -*- coding: utf-8 -*-

from urllib.parse import urljoin
from bs4 import BeautifulSoup

from scraper.fetch import fetch_html
from utils.storage import load_json


BASE = "https://goyabu.io"
RULES_PATH = "rules/goyabu.json"


def get_anime_list(page=1):
    rules = load_json(RULES_PATH, default={})

    url = f"{BASE}/lista-de-animes/page/{page}?l=todos&pg={page}"
    html = fetch_html(url)

    if not html or len(html) < 500:
        print("[LIST] HTML inválido ou vazio")
        return []

    soup = BeautifulSoup(html, "html.parser")

    card_selector = rules.get("anime_card", "article")
    link_selector = rules.get("anime_link", "a[href]")

    animes = []

    cards = soup.select(card_selector)

    # 🔥 fallback automático
    if not cards:
        print("[LIST] Seletor falhou, usando fallback")
        cards = soup.find_all("article")

    for card in cards:
        a = card.select_one(link_selector)
        if not a or not a.get("href"):
            continue

        name = a.get_text(" ", strip=True)
        link = urljoin(BASE, a["href"])

        # proteção básica
        if len(name) < 2 or not link.startswith("http"):
            continue

        animes.append({
            "name": name,
            "url": link
        })

    print(f"[LIST] Página {page}: {len(animes)} animes")
    return animes
