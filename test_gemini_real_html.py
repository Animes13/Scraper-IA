import os
import re
import json
import base64
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError
from google import genai
from bs4 import BeautifulSoup

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
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ))

        print(f"[PLAYWRIGHT] Abrindo: {url}")
        page.goto(url, timeout=60000)

        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=30000)
            except TimeoutError:
                print(f"[WARN] Seletor {wait_selector} não encontrado")

        for _ in range(scroll_times):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(1500)

        html = page.content()
        browser.close()
        return html

# =============================
# DETECÇÃO DE LINKS DE EPISÓDIOS
# =============================

def extract_episode_links(html):
    """Tenta detectar links de episódios do site"""
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(".episodes-grid") or soup.select_one("#episodes-container")
    links = []

    if container:
        for a in container.select("a[href]"):
            href = a["href"]
            if re.match(r"https://goyabu\.io/\d+", href):
                links.append(href)
    else:
        # fallback: busca JS allEpisodes
        m = re.search(r"const\s+allEpisodes\s*=\s*(\[[\s\S]*?\]);", html)
        if m:
            try:
                eps = json.loads(m.group(1).replace("\\/", "/"))
                eps.sort(key=lambda e: int(e.get("episodio", 0)))
                links = [f"https://goyabu.io/{ep['id']}" for ep in eps]
            except:
                pass
        # fallback genérico: qualquer link numérico
        if not links:
            ids = re.findall(r"https://goyabu\.io/(\d+)", html)
            links = [f"https://goyabu.io/{i}" for i in ids]

    return list(dict.fromkeys(links))

# =============================
# FUNÇÕES DE AJUDA
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

anime_html = fetch_html(ANIME_URL)
anime_slug = "black_clover"
with open(f"{DATA_DIR}/anime_{anime_slug}.html", "w", encoding="utf-8") as f:
    f.write(anime_html)
print(f"[OK] HTML do anime salvo em {DATA_DIR}/anime_{anime_slug}.html")

episode_links = extract_episode_links(anime_html)
if not episode_links:
    raise RuntimeError("Nenhum link de episódio encontrado — HTML salvo para análise futura")

first_ep_url = episode_links[0]
print(f"[OK] Primeiro episódio detectado: {first_ep_url}")

# =============================
# PASSO 2: IA ANALISA ANIME PAGE
# =============================

anime_prompt = f"""
Responda apenas com JSON puro.
Você é uma IA especialista em scraping adaptativo.

Objetivo:
- Detectar container da lista de episódios
- Detectar link de cada episódio
- Retornar null se não existir
- Tente pensar onde os episódios estão, mesmo que o layout mude

HTML:
{anime_html[:80000]}
"""

anime_response = client.models.generate_content(model=MODEL, contents=anime_prompt)
anime_rules = extract_json(anime_response.text)

# =============================
# PASSO 3: PÁGINA DO PRIMEIRO EPISÓDIO
# =============================

ep_html = fetch_html(first_ep_url)
with open(f"{DATA_DIR}/episode_{anime_slug}.html", "w", encoding="utf-8") as f:
    f.write(ep_html)
print(f"[OK] HTML do episódio salvo em {DATA_DIR}/episode_{anime_slug}.html")

episode_prompt = f"""
Responda apenas com JSON puro.
Você é uma IA especialista em scraping adaptativo.

Objetivo:
- Detectar botão do player
- Detectar iframe do player
- Detectar URL Blogger
- Retornar null se não existir
- Tente aprender o padrão do player para futuras alterações do site

HTML:
{ep_html[:80000]}
"""

ep_response = client.models.generate_content(model=MODEL, contents=episode_prompt)
episode_rules = extract_json(ep_response.text)

# =============================
# RESULTADO FINAL
# =============================

final_rules = {
    "anime_page": anime_rules,
    "episode_page": episode_rules,
    "episode_links_detected": episode_links
}

with open(f"{RULES_DIR}/goyabu.json", "w", encoding="utf-8") as f:
    json.dump(final_rules, f, indent=2, ensure_ascii=False)

print("\n[IA] REGRAS FINAIS GERADAS:\n")
print(json.dumps(final_rules, indent=2, ensure_ascii=False))
print(f"\n[OK] Regras salvas em {RULES_DIR}/goyabu.json")
