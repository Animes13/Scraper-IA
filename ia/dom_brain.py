# ia/dom_brain.py
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from collections import Counter
import re


def analyze_dom(html: str, context: str = None) -> dict:
    """
    Analisa o DOM e retorna seletores CSS prováveis
    """
    soup = BeautifulSoup(html, "html.parser")
    rules = {}

    # ============================
    # 1️⃣ Detectar cards repetidos
    # ============================
    articles = soup.find_all("article")
    if len(articles) >= 3:
        rules["anime_card"] = "article"

    # fallback: divs muito repetidas
    div_classes = []
    for div in soup.find_all("div"):
        if div.get("class"):
            div_classes.append(".".join(div.get("class")))

    if div_classes:
        common_div = Counter(div_classes).most_common(1)[0]
        if common_div[1] >= 3:
            rules["anime_card"] = f"div.{common_div[0]}"

    # ============================
    # 2️⃣ Detectar links principais
    # ============================
    links = soup.find_all("a", href=True)
    hrefs = [a["href"] for a in links]

    anime_like = [
        h for h in hrefs
        if re.search(r"/anime|/episodio|/episode|/assistir", h)
    ]

    if anime_like:
        rules["anime_link"] = "a[href]"

    # ============================
    # 3️⃣ Detectar botão de player
    # ============================
    buttons = soup.find_all("button")
    button_classes = []

    for btn in buttons:
        if btn.get("class"):
            button_classes.append(".".join(btn.get("class")))

    if button_classes:
        common_btn = Counter(button_classes).most_common(1)[0]
        rules["player_button"] = f"button.{common_btn[0]}"

    # ============================
    # 4️⃣ Detectar iframe (fallback)
    # ============================
    if soup.find("iframe"):
        rules["player_iframe"] = "iframe"

    return rules
