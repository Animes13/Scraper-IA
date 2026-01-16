import os
import re
import json
from playwright.sync_api import sync_playwright, TimeoutError
from google import genai
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import base64
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
os.makedirs(DATA_DIR, exist_ok=True)

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

        # scroll para disparar carregamento dinâmico
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
    """Tenta extrair links de episódios do HTML"""
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(".episodes-grid") or soup.select_one("#episodes-container")
    links = []

    if container:
        for a in container.select("a[href]"):
            href = a["href"]
            if re.match(r"https://goyabu\.io/\d+", href):
                links.append(href)
    else:
        # fallback: busca qualquer link numérico no HTML
        links = re.findall(r"https://goyabu\.io/(\d+)", html)
        links = [f"https://goyabu.io/{i}" for i in links]

    return list(dict.fromkeys(links))  # remove duplicados

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
        # VIDEO_CONFIG antigo
        m = re.search(r'VIDEO_CONFIG\s*=\s*({.*?});', html, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            streams = data.get("streams", [])
            if streams:
                streams.sort(key=lambda x: int(x.get("format_id", 0)), reverse=True)
                return streams[0].get("play_url") or streams[0].get("url")
        # ytInitialPlayerResponse novo
        m = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});', html, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            formats = (data.get("streamingData", {}).get("formats", []) +
                       data.get("streamingData", {}).get("adaptiveFormats", []))
            for f in formats:
                url = f.get("url")
                if url and "googlevideo.com" in url:
                    return url
        # fallback regex direto
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
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
html_file = os.path.join(DATA_DIR, f"anime_black_clover_{timestamp}.html")

with open(html_file, "w", encoding="utf-8") as f:
    f.write(anime_html)
print(f"[OK] HTML salvo em {html_file}")

episode_links = extract_episode_links(anime_html)
if not episode_links:
    print(f"[WARN] Nenhum link de episódio encontrado — HTML salvo para análise futura")
    episode_links = []

first_ep_url = episode_links[0] if episode_links else None
if first_ep_url:
    print(f"[OK] Primeiro episódio detectado: {first_ep_url}")
else:
    print("[WARN] Não há episódios detectados — workflow continua para salvar regras e HTML")

# =============================
# IA – PÁGINA DO ANIME (ADAPTATIVO)
# =============================

anime_prompt = f"""
Responda apenas com JSON puro.
Você é uma IA especialista em scraping adaptativo.

Objetivo:
- Detectar o container da lista de episódios
- Detectar link de cada episódio
- Retornar null se não existir
- Tente pensar onde os episódios estão, mesmo que o layout mude

HTML:
{anime_html[:80000]}
"""

anime_response = client.models.generate_content(
    model=MODEL,
    contents=anime_prompt
)
anime_rules = extract_json(anime_response.text)

# =============================
# PASSO 2: PÁGINA DO EPISÓDIO
# =============================

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
- Tente aprender o padrão do player para futuras alterações do site

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
# RESULTADO FINAL
# =============================

final_rules = {
    "anime_page": anime_rules,
    "episode_page": episode_rules,
    "episode_links_detected": episode_links
}

rules_file = os.path.join("rules", "goyabu.json")
os.makedirs("rules", exist_ok=True)
with open(rules_file, "w", encoding="utf-8") as f:
    json.dump(final_rules, f, indent=2, ensure_ascii=False)

print("\n[IA] REGRAS FINAIS GERADAS:\n")
print(json.dumps(final_rules, indent=2, ensure_ascii=False))
print(f"\n[OK] Regras salvas em {rules_file}")
