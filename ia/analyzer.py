# ia/analyzer.py
# -*- coding: utf-8 -*-

import json
import os
from utils.storage import load_json, save_json
from google import genai

RULES_PATH = "rules/goyabu.json"

# Suporte a 5 APIs
API_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
]

SYSTEM_PROMPT = """
Você é um analisador de HTML para web scraping.
Sua tarefa APENAS identifica seletores CSS ou padrões regex.
NUNCA extraia nomes de filmes, animes ou episódios.
NUNCA explique nada.
Responda SOMENTE em JSON válido.
"""

def analyze_and_update_rules(html, context):
    """
    Analisa o HTML usando Gemini e atualiza o arquivo de regras.
    context: "episode_list" ou "stream"
    Retorna True se atualizou regras com sucesso.
    """
    rules = load_json(RULES_PATH, default={})

    if context == "episode_list":
        instruction = """
Analise o HTML e encontre onde os episódios estão definidos em JavaScript.
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

    # Tenta todas as APIs
    for idx, key in enumerate(API_KEYS, start=1):
        if not key:
            continue

        print(f"[IA] Tentando com GEMINI_API_KEY_{idx}...")
        try:
            # Configura a API
            genai.configure(api_key=key)

            # Chamada ao Gemini Chat
            response = genai.chat.completions.create(
                model="gemini-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": instruction + "\n\nHTML:\n" + html[:12000]}
                ],
                temperature=0
            )

            # Obtem o texto da resposta
            content = response.choices[0].message.content.strip()

            # Limpeza de possíveis ```json
            if content.startswith("```"):
                content = content.strip("`").replace("json", "", 1).strip()

            new_rules = json.loads(content)

            if isinstance(new_rules, dict):
                rules.update(new_rules)
                save_json(RULES_PATH, rules)
                print(f"[IA] Regras atualizadas usando API {idx}:", new_rules)
                return True
            else:
                print(f"[IA] Resposta inválida (não é dict) com API {idx}")

        except Exception as e:
            print(f"[IA] Falha ao analisar HTML usando API {idx}:", e)
            continue

    print("[IA] Todas as APIs falharam")
    return False
