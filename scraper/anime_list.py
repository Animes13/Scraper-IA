# scraper/anime_list.py
# -*- coding: utf-8 -*-

from urllib.parse import urljoin
from bs4 import BeautifulSoup

from scraper.fetch import fetch_html
from utils.storage import load_json, save_json
from utils.sanitizer import sanitize_html
from ia.analyzer import analyze_and_update_rules

BASE = "https://goyabu.io"
RULES_PATH = "rules/goyabu.json"


def get_anime_list(page=1):
    rules = load_json(RULES_PATH, default={})
    url = f"{BASE}/lista-de-animes/page/{page}?l=todos&pg={page}"
    html = fetch_html(url)

    if not html or len(html) < 500:
        print("[LIST] HTML inválido")
        return []

    soup = BeautifulSoup(html, "html.parser")
    card_selector = rules.get("anime_card", "article")
    link_selector = rules.get("anime_link", "a[href]")

    cards = soup.select(card_selector)
    ia_used = False

    if not cards:
        print("[LIST] Seletor falhou → acionando IA")
        old_rules = load_json(RULES_PATH, default={})

        clean_html = sanitize_html(html)
        ok = analyze_and_update_rules(clean_html, "anime_list")

        if ok:
            ia_used = True
            rules = load_json(RULES_PATH, default={})
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(rules.get("anime_card", "article"))

        if not cards:
            print("[LIST] IA falhou → rollback")
            save_json(RULES_PATH, old_rules)
            return []

    animes = []

    for card in cards:
        a = card.select_one(link_selector)
        if not a or not a.get("href"):
            continue

        name = a.get_text(" ", strip=True)
        link = urljoin(BASE, a["href"])

        if len(name) < 2:
            continue

        animes.append({
            "name": name,
            "url": link
        })

    print(f"[LIST] Página {page}: {len(animes)} animes (IA usada: {ia_used})")
    return animes
