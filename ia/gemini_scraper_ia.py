# gemini_scraper_ia.py
import os
import re
import json
import requests
from datetime import datetime
from google import genai  # ✅ novo import oficial

from rule_validator import validate

# =============================
# CONFIG
# =============================
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY não definida")

MODEL = "models/gemini-2.5-flash"
BASE_URL = "https://goyabu.io"
MAX_RETRIES = 4

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120.0"
}

# =============================
# PATHS
# =============================
HTML_DIR = "HTML"
RULES_DIR = "rules"

HTML_MAP = {
    "anime_list_page": f"{HTML_DIR}/anime_list",
    "anime_page": f"{HTML_DIR}/anime_page",
    "episode_page": f"{HTML_DIR}/episode_page",
}

RULES_MAP = {
    "anime_list_page": f"{RULES_DIR}/anime_list",
    "anime_page": f"{RULES_DIR}/anime_page",
    "episode_page": f"{RULES_DIR}/episode_page",
}

for d in list(HTML_MAP.values()) + list(RULES_MAP.values()):
    os.makedirs(d, exist_ok=True)

# =============================
# GEMINI CLIENT
# =============================
client = genai.Client(api_key=API_KEY)

# =============================
# UTIL
# =============================
def fetch_html(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.text


def save_html(html, page_type):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{HTML_MAP[page_type]}/{page_type}_{ts}.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 [OK] HTML salvo → {path}")
    return path


def extract_json(text):
    clean = re.sub(r"```(?:json)?", "", text, flags=re.I)
    clean = clean.strip("` \n\t")
    return json.loads(clean)


def save_rules(page_type, rules):
    path = f"{RULES_MAP[page_type]}/goyabu.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({page_type: rules}, f, indent=2, ensure_ascii=False)
    print(f"💾 [OK] Regras salvas → {path}")

# =============================
# 🔍 CLASSIFICADOR DE CONTEXTO
# =============================
def classify_html(html_map):
    context = {}

    anime_html = html_map["anime_page"]
    episode_html = html_map["episode_page"]

    context["anime_page"] = {
        "has_js_episodes": any(x in anime_html for x in ["data-list", "allEpisodes", "episodesJson"]),
        "has_html_episodes": any(x in anime_html for x in ["episode-item", "boxEP", "episodes"])
    }

    context["episode_page"] = {
        "has_iframe": "<iframe" in episode_html,
        "has_player_button": "player" in episode_html and "button" in episode_html,
        "has_blogger": any(x in episode_html for x in ["blogger", "googlevideo"])
    }

    return context

# =============================
# PROMPT
# =============================
def build_prompt(html_map, context, feedback=None):

    feedback_txt = ""
    if feedback:
        feedback_txt = f"""
FALHAS ANTERIORES (corrija):
{json.dumps(feedback, indent=2, ensure_ascii=False)}
"""

    return f"""
Responda APENAS com JSON válido.
NÃO explique.
NÃO use URLs fixas.
NÃO use números.
NÃO use textos específicos.

Você é uma IA especialista em SCRAPING GENÉRICO ADAPTATIVO.

CONTEXTO DETECTADO AUTOMATICAMENTE:
{json.dumps(context, indent=2, ensure_ascii=False)}

Estrutura obrigatória:
{{
  "anime_list_page": {{
    "container": null,
    "anime_card": null,
    "anime_link": null
  }},
  "anime_page": {{
    "episodes_container": null,
    "episode_link": null
  }},
  "episode_page": {{
    "player_iframe": null,
    "encrypted_attribute": null,
    "blogger_pattern": null
  }}
}}

REGRAS:
- CSS genérico e resiliente
- Não dependa de texto
- Não dependa de ordem
- Pense em múltiplos animes

{feedback_txt}

HTML — LISTA:
{html_map["anime_list_page"][:60000]}

HTML — ANIME:
{html_map["anime_page"][:60000]}

HTML — EPISÓDIO:
{html_map["episode_page"][:60000]}
"""

# =============================
# MAIN
# =============================
if __name__ == "__main__":

    print("🚀 Iniciando Gemini Scraper Adaptativo")

    urls = {
        "anime_list_page": f"{BASE_URL}/lista-de-animes/page/1?l=todos",
        "anime_page": f"{BASE_URL}/anime/black-clover-dublado",
        "episode_page": f"{BASE_URL}/44346",
    }

    html_map = {}

    for page_type, url in urls.items():
        print(f"🌐 Baixando {page_type} → {url}")
        html = fetch_html(url)
        save_html(html, page_type)
        html_map[page_type] = html

    context = classify_html(html_map)
    feedback = None
    best_score = 0

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🤖 Tentativa IA #{attempt}")

        prompt = build_prompt(html_map, context, feedback)

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        rules = extract_json(response.text)

        feedback = {}
        total_score = 0
        all_valid = True

        for page_type in rules:
            print(f"🧪 Validando {page_type}...")
            result = validate(
                page_type,
                html_map[page_type],
                rules[page_type],
                context=context
            )

            print(f"📊 Score: {result['score']} | Válido: {result['valid']}")
            total_score += result["score"]

            if not result["valid"]:
                all_valid = False
                feedback[page_type] = result

        if total_score < best_score:
            print("⚠️ Regressão detectada, descartando regras")
            continue

        best_score = total_score

        if all_valid:
            print("\n✅ REGRAS APROVADAS (100%) 🎯")
            for page_type in rules:
                save_rules(page_type, rules[page_type])
            print("🔥 IA ADAPTATIVA CONCLUÍDA")
            break

        print("🔁 Reanalisando com feedback...")
    else:
        print("\n❌ Falhou após várias tentativas. HTML altamente dinâmico.")