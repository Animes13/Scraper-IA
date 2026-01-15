# scraper/stream_resolver.py
# -*- coding: utf-8 -*-

import re
import requests
from bs4 import BeautifulSoup

from utils.storage import load_json
from ia.trainer import training_cycle

RULES_PATH = "rules/goyabu.json"


class StreamResolver:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 10) "
                "AppleWebKit/537.36 Chrome/120.0"
            ),
            "Referer": "https://goyabu.io/"
        })

        self.rules = load_json(RULES_PATH, default={})

    def resolve(self, episode_url):
        try:
            r = self.session.get(episode_url, timeout=20)
            r.raise_for_status()
        except Exception:
            return None

        html = r.text
        soup = BeautifulSoup(html, "html.parser")

        # 1️⃣ Botão aprendido
        btn_selector = self.rules.get(
            "player_button",
            "button[data-blogger-url-encrypted]"
        )

        btn = soup.select_one(btn_selector)
        if btn:
            enc = btn.get("data-blogger-url-encrypted")
            if enc:
                blogger = self._decrypt_blogger(enc)
                if blogger:
                    return self._resolve_blogger(blogger)

        # 2️⃣ Regex fallback
        regex = self.rules.get(
            "blogger_regex",
            r'https://www\.blogger\.com/video\.g[^"]+'
        )

        m = re.search(regex, html)
        if m:
            return self._resolve_blogger(m.group(0))

        # ❌ Falhou → treina IA
        training_cycle(
            context="stream",
            html=html,
            rules_used=self.rules,
            success=False
        )

        return None

    def _resolve_blogger(self, blogger_url):
        try:
            r = self.session.get(blogger_url, timeout=20)
            r.raise_for_status()
        except Exception:
            return None

        m = re.search(
            r'(https://[^\s"]+googlevideo\.com/[^\s"]+)',
            r.text
        )

        return m.group(1) if m else None

    def _decrypt_blogger(self, encrypted):
        # sua função real entra aqui
        return None
