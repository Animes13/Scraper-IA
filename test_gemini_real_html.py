import os
import re
import json
from playwright.sync_api import sync_playwright, TimeoutError
from google import genai
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import base64

# =============================
# CONFIGURAÇÃO
# =============================

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY não definida")

ANIME_URL = "https://goyabu.io/anime/black-clover-dublado"
client = genai.Client(api_key=API_KEY)
MODEL = "models/gemini-2.5-flash"

# =============================
# FUNÇÃO JSON SEGURO
# =============================

def extract_json(text):
    clean = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    clean = clean.strip("` \n\t")
    return json.loads(clean)

# =============================
# FETCH HTML COM SCROLL
# =============================

def fetch_html(url, wait_selector=None, scroll_times=5):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        print(f"[PLAYWRIGHT] Abrindo: {url}")
        page.goto(url, timeout=60000)

        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=30000)
            except TimeoutError:
                print(f"[WARN] Seletor {wait_selector} não encontrado")

        # scroll para disparar carregamento dinâmico
        for _ in range(scroll_times):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(1500)

        html = page.content()
        browser.close()
        return html

# =============================
# EXTRAI LINKS DE EPISÓDIOS
# =============================

def extract_episode_links(html):
    links = re.findall(r"https://goyabu\.io/(\d+)", html)
    return list(dict.fromkeys(links))  # remove duplicados

# =============================
# FUNÇÕES DE AJUDA DO ADDON
# =============================

def decrypt_blogger_url(encrypted):
    try:
        if not encrypted:
            return None
        encrypted = encrypted.strip()
        missing = len(encrypted) % 4
        if missing:
            encrypted += "=" * (4 - missing)
        decoded = base64.b64decode(encrypted).decode("utf-8", errors="ignore")
        return decoded[::-1].strip() if decoded.startswith("http") else None
    except:
        return None

def extract_blogger_googlevideo(html):
    try:
        if not html:
            return None
        m = re.search(r'VIDEO_CONFIG\s*=\s*({.*?});', html, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            streams = data.get("streams", [])
            if streams:
                streams.sort(key=lambda x: int(x.get("format_id", 0)), reverse=True)
                return streams[0].get("play_url") or streams[0].get("url")
        m = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});', html, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            formats = (data.get("streamingData", {}).get("formats", []) +
                       data.get("streamingData", {}).get("adaptiveFormats", []))
            for f in formats:
                url = f.get("url")
                if url and "googlevideo.com" in url:
                    return url
        m = re.search(r'(https://[^"\']+googlevideo\.com/videoplayback[^"\']+)', html)
        if m:
            return m.group(1)
        return None
    except:
        return None

# =============================
# PASSO 1: PÁGINA DO ANIME
# =============================

anime_html = fetch_html(ANIME_URL, wait_selector=".episodes-grid")
episode_ids = extract_episode_links(anime_html)

if not episode_ids:
    raise RuntimeError("Nenhum link de episódio encontrado")

first_ep_url = f"https://goyabu.io/{episode_ids[0]}"
print(f"[OK] Primeiro episódio detectado: {first_ep_url}")

# =============================
# IA ANALISA ANIME PAGE
# =============================

anime_prompt = f"""
Responda APENAS com JSON puro.

Você está analisando a PÁGINA DO ANIME do site goyabu.io.
Objetivo:
- Identificar o container da lista de episódios
- Identificar link de cada episódio

REGRAS:
- Use SOMENTE elementos presentes no HTML
- URLs de episódios são numéricas (ex: /37475)
- Retorne null se não existir

JSON esperado:
{{
  "episode_list": "CSS selector ou null",
  "episode_link": "CSS selector ou null",
  "observacoes": "explicação curta"
}}

HTML:
{anime_html[:50000]}
"""

anime_response = client.models.generate_content(
    model=MODEL,
    contents=anime_prompt
)
anime_rules = extract_json(anime_response.text)

# =============================
# PASSO 2: PÁGINA DO EPISÓDIO
# =============================

ep_html = fetch_html(first_ep_url)
episode_prompt = f"""
Responda APENAS com JSON puro.

Você está analisando a PÁGINA DO EPISÓDIO do site goyabu.io.
Objetivo:
- Detectar botão do player
- Detectar iframe do player
- Detectar URL Blogger

IMPORTANTE:
- Blogger pode estar em iframe, script JS ou data-src
- Retorne null se não existir

JSON esperado:
{{
  "player_button": "CSS selector ou null",
  "iframe_selector": "CSS selector ou null",
  "blogger_regex": "regex ou null",
  "observacoes": "explicação curta"
}}

HTML:
{ep_html[:50000]}
"""

ep_response = client.models.generate_content(
    model=MODEL,
    contents=episode_prompt
)
episode_rules = extract_json(ep_response.text)

# =============================
# RESULTADO FINAL
# =============================

final_rules = {
    "anime_page": anime_rules,
    "episode_page": episode_rules
}

print("\n[IA] REGRAS FINAIS GERADAS:\n")
print(json.dumps(final_rules, indent=2, ensure_ascii=False))

os.makedirs("rules", exist_ok=True)
with open("rules/goyabu.json", "w", encoding="utf-8") as f:
    json.dump(final_rules, f, indent=2, ensure_ascii=False)

print("\n[OK] Regras salvas em rules/goyabu.json")
