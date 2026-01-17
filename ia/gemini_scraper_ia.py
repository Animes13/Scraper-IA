# gemini_scraper_ia.py
import os
import re
import json
import requests
from datetime import datetime
from google import genai  # API oficial Gemini

from rule_validator import validate  # 🔥 VALIDADOR

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
# DIRETÓRIOS
# =============================
HTML_DIR = "HTML"
RULES_DIR = "rules"

HTML_MAP = {
    "anime_list_page": os.path.join(HTML_DIR, "anime_list"),
    "anime_page": os.path.join(HTML_DIR, "anime_page"),
    "episode_page": os.path.join(HTML_DIR, "episode_page"),
}

RULES_MAP = {
    "anime_list_page": os.path.join(RULES_DIR, "anime_list"),
    "anime_page": os.path.join(RULES_DIR, "anime_page"),
    "episode_page": os.path.join(RULES_DIR, "episode_page"),
}

for d in list(HTML_MAP.values()) + list(RULES_MAP.values()):
    os.makedirs(d, exist_ok=True)

# =============================
# CLIENT GEMINI
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
    path = os.path.join(HTML_MAP[page_type], f"{page_type}_{ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 [OK] HTML salvo → {path}")
    return path


def extract_json(text):
    clean = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    clean = clean.strip("` \n\t")
    return json.loads(clean)


def save_rules(page_type, rules):
    path = os.path.join(RULES_MAP[page_type], "goyabu.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({page_type: rules}, f, indent=2, ensure_ascii=False)
    print(f"💾 [OK] Regras salvas → {path}")


# =============================
# PROMPT BASE
# =============================
def build_prompt(html_map, feedback=None):
    feedback_txt = ""
    if feedback:
        feedback_txt = f"""
REANÁLISE OBRIGATÓRIA:
A regra anterior falhou pelos motivos abaixo.
Corrija e melhore.

FALHAS DETECTADAS:
{json.dumps(feedback, indent=2, ensure_ascii=False)}
"""

    return f"""
Responda APENAS com JSON puro.
NÃO explique.
NÃO use URLs fixas.
NÃO use números específicos.
NÃO liste links reais.

Você é uma IA especialista em scraping GENÉRICO e ADAPTATIVO.
Suas regras DEVEM funcionar em múltiplos animes.

Estrutura OBRIGATÓRIA:

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
- Use SOMENTE CSS genérico
- NÃO dependa de texto fixo
- NÃO dependa de ordem exata
- Pense como um scraper resiliente

{feedback_txt}

HTML — LISTA DE ANIMES:
{html_map["anime_list_page"][:60000]}

HTML — PÁGINA DO ANIME:
{html_map["anime_page"][:60000]}

HTML — PÁGINA DO EPISÓDIO:
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

    # 🔹 FETCH + SAVE HTML
    for page_type, url in urls.items():
        print(f"🌐 Baixando {page_type} → {url}")
        html = fetch_html(url)
        save_html(html, page_type)
        html_map[page_type] = html

    feedback = None

    # 🔁 LOOP ADAPTATIVO
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🤖 Tentativa IA #{attempt}")

        prompt = build_prompt(html_map, feedback)

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        rules = extract_json(response.text)

        all_valid = True
        feedback = {}

        # 🧪 VALIDAR CADA PÁGINA
        for page_type in ["anime_list_page", "anime_page", "episode_page"]:
            print(f"🧪 Validando {page_type}...")
            result = validate(
                page_type,
                html_map[page_type],
                rules.get(page_type, {}),
                base_url=BASE_URL
            )

            print(f"📊 Score: {result['score']} | Válido: {result['valid']}")

            if not result["valid"]:
                all_valid = False
                feedback[page_type] = result

        # ✅ SUCESSO
        if all_valid:
            print("\n✅ REGRAS APROVADAS (100%) 🎯")
            for page_type in rules:
                save_rules(page_type, rules[page_type])
            print("\n🔥 IA FINALMENTE APRENDEU SOZINHA")
            break

        print("🔁 Regras insuficientes, reanalisando automaticamente...")

    else:
        print("\n❌ Falhou após várias tentativas. HTML pode estar muito dinâmico.")