import os
import re
import json
import requests
from google import genai
from bs4 import BeautifulSoup
from datetime import datetime

# =============================
# CONFIGURAÇÃO
# =============================
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY não definida")

ANIME_URL = "https://goyabu.io/anime/black-clover-dublado"
client = genai.Client(api_key=API_KEY)
MODEL = "models/gemini-2.5-flash"

DATA_DIR = "data"
RULES_DIR = "rules"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RULES_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Kodi) "
        "AppleWebKit/537.36 Chrome/120.0"
    )
}

# =============================
# JSON SEGURO
# =============================
def extract_json(text):
    clean = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    clean = clean.strip("` \n\t")
    return json.loads(clean)

# =============================
# FETCH HTML
# =============================
def fetch_html(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.text

# =============================
# EXTRAI LINKS DE EPISÓDIOS
# =============================
def extract_episode_links(html):
    links = []
    m = re.search(r"const allEpisodes\s*=\s*(\[[\s\S]*?\]);", html)
    if m:
        eps = json.loads(m.group(1).replace("\\/", "/"))
        eps.sort(key=lambda e: int(e.get("episodio", 0)))
        for ep in eps:
            links.append(f"https://goyabu.io/{ep['id']}")
    return links

# =============================
# SALVA HTML COM TIMESTAMP
# =============================
def save_html(html, name="anime_black_clover"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(DATA_DIR, f"{name}_{timestamp}.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] HTML salvo em {filepath}")
    return filepath

# =============================
# MAIN
# =============================
anime_html = fetch_html(ANIME_URL)
save_html(anime_html)

episode_links = extract_episode_links(anime_html)
first_ep_url = episode_links[0] if episode_links else None
if first_ep_url:
    print(f"[OK] Primeiro episódio detectado: {first_ep_url}")
else:
    print("[WARN] Nenhum episódio detectado — workflow continua")

# =============================
# IA GEMINI – ADAPTATIVO
# =============================
anime_prompt = f"""
Responda apenas com JSON puro.
Você é uma IA especialista em scraping adaptativo.

Objetivo:
- Detectar container da lista de episódios
- Detectar link de cada episódio
- Retornar null se não existir

HTML:
{anime_html[:80000]}
"""

anime_response = client.models.generate_content(
    model=MODEL,
    contents=anime_prompt
)
anime_rules = extract_json(anime_response.text)

# Página do episódio
if first_ep_url:
    ep_html = fetch_html(first_ep_url)
    ep_prompt = f"""
Responda apenas com JSON puro.
Você é uma IA especialista em scraping adaptativo.

Objetivo:
- Detectar botão do player
- Detectar iframe do player
- Detectar URL Blogger
- Retornar null se não existir

HTML:
{ep_html[:80000]}
"""
    ep_response = client.models.generate_content(
        model=MODEL,
        contents=ep_prompt
    )
    episode_rules = extract_json(ep_response.text)
else:
    episode_rules = {}

# =============================
# SALVA REGRAS
# =============================
final_rules = {
    "anime_page": anime_rules,
    "episode_page": episode_rules,
    "episode_links_detected": episode_links
}

rules_file = os.path.join(RULES_DIR, "goyabu.json")
with open(rules_file, "w", encoding="utf-8") as f:
    json.dump(final_rules, f, indent=2, ensure_ascii=False)

print("\n[IA] REGRAS FINAIS GERADAS:\n")
print(json.dumps(final_rules, indent=2, ensure_ascii=False))
print(f"\n[OK] Regras salvas em {rules_file}")
