# ia/analyzer.py
# -*- coding: utf-8 -*-

import json
import os
from utils.storage import load_json, save_json
import google.generativeai as genai

RULES_PATH = "rules/goyabu.json"

# Configura API Gemini
genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-3-pro-preview")

SYSTEM_PROMPT = """
Você é um analisador de HTML para web scraping.
Sua tarefa é APENAS identificar seletores CSS ou padrões regex.
NUNCA extraia nomes de filmes, animes ou episódios.
NUNCA explique nada.
Responda SOMENTE em JSON válido.
"""

def analyze_and_update_rules(html, context):
    rules = load_json(RULES_PATH, default={})

    if context == "episode_list":
        instruction = """
Analise o HTML e encontre onde os episódios estão definidos
em JavaScript.

Retorne EXATAMENTE neste formato:
{
  "episode_js_key": "const allEpisodes",
  "episode_regex": "regex_aqui"
}
"""
    elif context == "stream":
        instruction = """
Analise o HTML e encontre o player de vídeo.

Retorne EXATAMENTE neste formato:
{
  "player_button": "seletor_css",
  "blogger_regex": "regex_aqui"
}
"""
    else:
        return False

    prompt = (
        SYSTEM_PROMPT
        + "\n\n"
        + instruction
        + "\n\nHTML (resumido):\n"
        + html[:12000]   # 🔥 limita tokens
    )

    try:
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt
        )

        content = response.text.strip()

        # Proteção: Gemini às vezes envolve em ```json
        if content.startswith("```"):
            content = content.strip("`")
            content = content.replace("json", "", 1).strip()

        new_rules = json.loads(content)

    except Exception as e:
        print("[IA] Falha ao analisar HTML:", e)
        return False

    # Validação mínima
    if not isinstance(new_rules, dict):
        print("[IA] Resposta inválida (não é dict)")
        return False

    rules.update(new_rules)
    save_json(RULES_PATH, rules)

    print("[IA] Regras atualizadas:", new_rules)
    return True
