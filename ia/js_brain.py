# ia/js_brain.py
# -*- coding: utf-8 -*-

import re
import json
from collections import Counter


def analyze_js(html: str) -> dict:
    """
    Analisa JS embutido no HTML e tenta descobrir
    como os episódios estão definidos.
    """
    rules = {}

    # ============================
    # 1️⃣ Procurar arrays JS comuns
    # ============================
    patterns = {
        "allEpisodes": r"const\s+allEpisodes\s*=\s*(\[[\s\S]*?\])\s*;",
        "episodes": r"var\s+episodes\s*=\s*(\[[\s\S]*?\])\s*;",
        "eps": r"(?:const|var)\s+eps\s*=\s*(\[[\s\S]*?\])\s*;"
    }

    matches = []

    for key, regex in patterns.items():
        match = re.search(regex, html)
        if match:
            matches.append((key, regex, match.group(1)))

    if not matches:
        return rules

    # ============================
    # 2️⃣ Escolher o mais confiável
    # ============================
    key, regex, raw = matches[0]

    rules["episode_js_key"] = key
    rules["episode_regex"] = regex

    # ============================
    # 3️⃣ Tentar validar JSON
    # ============================
    try:
        cleaned = raw.replace("\\/", "/")
        data = json.loads(cleaned)

        if isinstance(data, list) and len(data) > 0:
            rules["episode_format"] = "array"
            rules["episode_sample_keys"] = list(data[0].keys())

    except Exception:
        rules["episode_format"] = "js-array"

    return rules
