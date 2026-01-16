import os
import json
import re
from playwright.sync_api import sync_playwright, TimeoutError
from google import genai

# =============================
# CONFIG
# =============================

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY não definida")

ANIME_URL = "https://goyabu.io/anime/black-clover-dublado"
client = genai.Client(api_key=API_KEY)
MODEL = "models/gemini-2.5-flash"

# =============================
# JSON SAFE PARSER
# =============================
def extract_json(text):
    clean = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    clean = clean.strip("` \n\t")
    return json.loads(clean)

# =============================
# PLAYWRIGHT FETCH COM SCROLL
# =============================
def fetch_html(url):
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
        page.wait_for_load_state("domcontentloaded")

        # força execução de JS (scroll para disparar carregamento)
        for _ in range(5):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(1500)

        html = page.content()
        browser.close()
        return html

# =============================
# 1️⃣ ANIME PAGE
# =============================
print("[STEP 1] Capturando página do anime...")
anime_html = fetch_html(ANIME_URL)

if "<body" not in anime_html.lower():
    raise RuntimeError("HTML do anime inválido")

# =============================
# IA – ANIME PAGE
# =============================
anime_prompt = f"""
Responda APENAS com JSON puro.

Você está analisando a PÁGINA DO ANIME do site goyabu.io.

Objetivo:
- Identificar onde está a LISTA de episódios
- Identificar o LINK individual de cada episódio

REGRAS:
- Use SOMENTE elementos presentes no HTML
- Episódios possuem URLs numéricas (ex: /37475)
- NÃO invente seletores
- Se não houver lista ou links detectáveis, retorne null e explique

JSON esperado:

{{
  "episode_list": "CSS selector ou null",
  "episode_link": "CSS selector ou null",
  "observacoes": "curta explicação"
}}

HTML:
{anime_html[:50000]}
"""

print("[IA] Analisando página do anime...")
anime_response = client.models.generate_content(
    model=MODEL,
    contents=anime_prompt
)
anime_rules = extract_json(anime_response.text)

# =============================
# 2️⃣ DETECTAR PRIMEIRO EPISÓDIO (IA fallback)
# =============================
print("[STEP 2] Detectando primeiro episódio real...")

# tenta extrair via JS first (allEpisodes)
m = re.search(r"const\s+allEpisodes\s*=\s*(\[[\s\S]*?\]);", anime_html)
first_id = None

if m:
    try:
        eps = json.loads(m.group(1).replace("\\/", "/"))
        if eps:
            eps.sort(key=lambda e: int(e.get("episodio", 0)))
            first_id = eps[0]["id"]
            print(f"[OK] Episódio detectado via JS: {first_id}")
    except Exception as e:
        print(f"[WARN] Falha ao parsear allEpisodes: {e}")

# fallback: detectar link numérico diretamente do HTML
if not first_id:
    match = re.search(r'https://goyabu\.io/(\d+)', anime_html)
    if match:
        first_id = match.group(1)
        print(f"[OK] Episódio detectado via HTML: {first_id}")

if not first_id:
    raise RuntimeError("Nenhum link de episódio encontrado no HTML do anime")

EP_URL = f"https://goyabu.io/{first_id}"
ep_html = fetch_html(EP_URL)

if "<body" not in ep_html.lower():
    raise RuntimeError("HTML do episódio inválido")

# =============================
# IA – EPISODE PAGE
# =============================
episode_prompt = f"""
Responda APENAS com JSON puro.

Você está analisando a PÁGINA DO EPISÓDIO do site goyabu.io.

Objetivo:
- Detectar botão ou ação que leva ao player
- Detectar iframe do player
- Detectar URL Blogger (direta ou indireta)

IMPORTANTE:
- Blogger pode estar em iframe, script JS ou atributo data-src
- NÃO invente dados
- Use null se não existir
- Explique no campo observacoes como detectou cada elemento

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

print("[IA] Analisando página do episódio...")
ep_response = client.models.generate_content(
    model=MODEL,
    contents=episode_prompt
)
episode_rules = extract_json(ep_response.text)

# =============================
# 3️⃣ RESULTADO FINAL
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
