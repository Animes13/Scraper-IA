# scraper/stream_resolver.py
# -*- coding: utf-8 -*-

import re
import requests
from bs4 import BeautifulSoup

from utils.storage import load_json

RULES_PATH = "rules/goyabu.json"


class StreamResolver:

    def __init__(self):
        self.ua = (
            "Mozilla/5.0 (Linux; Android 10; Pixel 5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Mobile Safari/537.36"
        )

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.ua,
            "Referer": "https://goyabu.io/"
        })

        self.rules = load_json(RULES_PATH)

    def resolve(self, episode_url):
        try:
            r = self.session.get(episode_url, timeout=20)
            r.raise_for_status()
        except Exception:
            return None

        html = r.text
        soup = BeautifulSoup(html, "html.parser")

        # 1️⃣ Botão criptografado (regra aprendida)
        btn_selector = self.rules.get(
            "player_button",
            "button.player-tab[data-blogger-url-encrypted]"
        )

        btn = soup.select_one(btn_selector)
        if btn:
            enc = btn.get("data-blogger-url-encrypted")
            if enc:
                blogger = self._decrypt_blogger(enc)
                if blogger:
                    return self._resolve_blogger(blogger)

        # 2️⃣ Fallback regex
        regex = self.rules.get(
            "blogger_regex",
            r'https://www\.blogger\.com/video\.g[^"]+'
        )

        m = re.search(regex, html)
        if m:
            return self._resolve_blogger(m.group(0))

        return None

    # ==========================
    # BLOGGER → GOOGLEVIDEO
    # ==========================
    def _resolve_blogger(self, blogger_url):
        try:
            r = self.session.get(blogger_url, timeout=20)
            r.raise_for_status()
        except Exception:
            return None

        html = r.text

        # 🔥 Extração simples (IA pode melhorar depois)
        m = re.search(
            r'(https://[^\s"]+googlevideo\.com/[^\s"]+)',
            html
        )

        if not m:
            return None

        return m.group(1)

    # ==========================
    # PLACEHOLDER (sua função real entra aqui)
    # ==========================
    def _decrypt_blogger(self, encrypted):
        # 👉 aqui você cola sua função real decrypt_blogger_url
        return None
