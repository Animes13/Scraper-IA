# ia/analyzer.py
# -*- coding: utf-8 -*-

import json
import os
from utils.storage import load_json, save_json
import google.generativeai as genai

RULES_PATH = "rules/goyabu.json"

# Configuração de múltiplas APIs (até 5)
API_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
]

MODELS = [
    "gemini-3-pro-preview",
    "gemini-3-pro-preview",
    "gemini-3-pro-preview",
    "gemini-3-pro-preview",
    "gemini-3-pro-preview",
]

SYSTEM_PROMPT = """
Você é um analisador de HTML para web scraping.
Sua tarefa é APENAS identificar seletores CSS ou padrões regex.
NUNCA extraia nomes de filmes, animes ou episódios.
NUNCA explique nada.
Responda SOMENTE em JSON válido.
"""

def analyze_and_update_rules(html, context, api_index=0):
    """
    html: conteúdo HTML
    context: "episode_list" ou "stream"
    api_index: índice da API/KEY a usar (0-4)
    """
    if api_index < 0 or api_index >= len(API_KEYS):
        print("[IA] Índice de API inválido, usando 0")
        api_index = 0

    genai.configure(api_key=API_KEYS[api_index])
    model = genai.GenerativeModel(MODELS[api_index])

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
        + html[:12000]
    )

    try:
        response = model.generate_content(
            model=MODELS[api_index],
            contents=prompt
        )

        content = response.text.strip()

        # Proteção: Gemini às vezes envolve em ```json
        if content.startswith("```"):
            content = content.strip("`")
            content = content.replace("json", "", 1).strip()

        new_rules = json.loads(content)

    except Exception as e:
        print(f"[IA] Falha ao analisar HTML usando API {api_index+1}:", e)
        return False

    if not isinstance(new_rules, dict):
        print("[IA] Resposta inválida (não é dict)")
        return False

    rules.update(new_rules)
    save_json(RULES_PATH, rules)

    print(f"[IA] Regras atualizadas usando API {api_index+1}:", new_rules)
    return True
