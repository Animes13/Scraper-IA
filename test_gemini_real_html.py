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

URL_TESTE = "https://goyabu.io/anime/black-clover-dublado"

client = genai.Client(api_key=API_KEY)
model = "models/gemini-2.5-flash"

# =============================
# FUNÇÃO: EXTRAI JSON SEGURO
# =============================

def extract_json(text):
    clean = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    clean = clean.strip("` \n\t")
    return json.loads(clean)

# =============================
# 1️⃣ BAIXA HTML REAL
# =============================

print("[TESTE] Abrindo navegador real (Playwright)...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    )

    page.goto(URL_TESTE, timeout=60000)

    try:
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(3000)
    except TimeoutError:
        print("[WARN] Página pode não ter carregado tudo")

    html = page.content()
    browser.close()

print(f"[OK] HTML final capturado ({len(html)} chars)")

if "<body" not in html.lower():
    raise RuntimeError("HTML inválido")

# =============================
# 2️⃣ PROMPT IA (AVANÇADO)
# =============================

prompt = f"""
Responda APENAS com JSON puro, sem markdown.

Você é uma IA especialista em scraping adaptativo e sites de anime.

O site analisado (goyabu.io) possui DUAS ETAPAS:
1) Página do anime → lista de episódios
2) Página do episódio (/37475) → player real (Blogger)

Analise o HTML FINAL abaixo (renderizado com JavaScript).

REGRAS IMPORTANTES:
- NÃO invente seletores
- Use SOMENTE elementos realmente existentes
- Se algo não existir, retorne null
- Detecte links de episódio por IDs numéricos (/\\d+)
- Detecte player por botão, iframe ou JS
- Blogger pode estar em iframe, data-src ou script JS

Retorne EXATAMENTE este JSON:

{{
  "anime_page": {{
    "episode_list": "CSS selector ou null",
    "episode_link": "CSS selector ou null"
  }},
  "episode_page": {{
    "player_button": "CSS selector ou null",
    "iframe_selector": "CSS selector ou null",
    "blogger_regex": "regex ou null"
  }},
  "observacoes": "explicação curta e objetiva"
}}

HTML (parcial):
{html[:45000]}
"""

# =============================
# 3️⃣ IA
# =============================

print("[IA] Analisando HTML completo...")

response = client.models.generate_content(
    model=model,
    contents=prompt
)

rules = extract_json(response.text)

# =============================
# 4️⃣ SALVAR
# =============================

print("\n[IA] Regras geradas com sucesso:\n")
print(json.dumps(rules, indent=2, ensure_ascii=False))

os.makedirs("rules", exist_ok=True)
with open("rules/goyabu.json", "w", encoding="utf-8") as f:
    json.dump(rules, f, indent=2, ensure_ascii=False)

print("\n[OK] Regras salvas em rules/goyabu.json")
