# ia/analyzer.py
# -*- coding: utf-8 -*-

import os
import json
from utils.storage import load_json, save_json

from openai import OpenAI

RULES_PATH = "rules/goyabu.json"

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


SYSTEM_PROMPT = """
Você é um analisador de HTML para web scraping.
Sua tarefa é APENAS identificar seletores CSS ou padrões regex.
NUNCA extraia nomes de filmes, animes ou episódios.
Responda SOMENTE em JSON válido.
"""


def analyze_and_update_rules(html, context):
    rules = load_json(RULES_PATH, default={})

    if context == "episode_list":
        instruction = """
Analise o HTML e encontre onde os episódios estão definidos.
Retorne:
{
  "episode_js_key": "...",
  "episode_regex": "..."
}
"""
    elif context == "stream":
        instruction = """
Analise o HTML e encontre o player de vídeo.
Retorne:
{
  "player_button": "seletor_css",
  "blogger_regex": "regex"
}
"""
    else:
        return

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction + "\nHTML:\n" + html}
        ],
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    try:
        new_rules = json.loads(content)
    except Exception:
        print("[IA] Resposta inválida")
        return

    rules.update(new_rules)
    save_json(RULES_PATH, rules)

    print("[IA] Regras atualizadas:", new_rules)
