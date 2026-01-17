# gemini_scraper_ia.py
import os
import re
import json
import requests
import google.generativeai as genai
from datetime import datetime
from bs4 import BeautifulSoup

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY não definida")

MODEL = "models/gemini-2.5-flash"
BASE_URL = "https://goyabu.io"
DATA_DIR = "HTML"
RULES_DIR = "rules"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RULES_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; Kodi) AppleWebKit/537.36 Chrome/120.0"
}

genai.api_key = API_KEY

# =============================
# FETCH HTML
# =============================
def fetch_html(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.text

def save_html(html, name="page"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DATA_DIR, f"{name}_{timestamp}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] HTML salvo em {path}")
    return path

def extract_json(text):
    clean = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip("` \n\t")
    return json.loads(clean)

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    # URL do anime de exemplo
    anime_url = f"{BASE_URL}/anime/black-clover-dublado"

    html = fetch_html(anime_url)
    save_html(html, "anime_black_clover")

    prompt = f"""
Responda apenas com JSON puro.
Você é uma IA especialista em scraping adaptativo.

Objetivo:
- Detectar container da lista de episódios
- Detectar link de cada episódio
- Retornar null se não existir

HTML:
{html[:80000]}
"""

    # ======= Correção =======
    response = genai.models.generate_content(
        model=MODEL,
        contents=[{"type": "text", "text": prompt}]
    )
    rules = extract_json(response.last["content"][0]["text"])
    # ========================

    rules_file = os.path.join(RULES_DIR, "goyabu.json")
    with open(rules_file, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)

    print(f"\n[IA] Regras salvas em {rules_file}")
    print(json.dumps(rules, indent=2, ensure_ascii=False))
