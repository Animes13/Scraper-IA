import os
import json
import re
import google.generativeai as genai
from playwright.sync_api import sync_playwright

# =============================
# CONFIG
# =============================

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY não definida")

URL_TESTE = "https://goyabu.io/anime/odayaka-kizoku-no-kyuuka-no-susume"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# =============================
# FUNÇÃO: EXTRAI JSON DA IA
# =============================

def extract_json(text):
    clean = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    clean = clean.strip("` \n\t")
    return json.loads(clean)

# =============================
# 1️⃣ BAIXA HTML REAL (JS RENDERIZADO)
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
    page.wait_for_timeout(5000)
    html = page.content()

    browser.close()

print(f"[OK] HTML real capturado ({len(html)} chars)")

# =============================
# 2️⃣ PROMPT PROFISSIONAL
# =============================

prompt = f"""
RESPONDA APENAS COM JSON PURO.
NÃO use markdown.
NÃO use ```json.
NÃO escreva nada fora do JSON.

Você é uma IA especialista em web scraping avançado.

Analise o HTML REAL abaixo de um site de anime.
Seu objetivo é identificar informações IMPLÍCITAS, como um humano faria.

Retorne um JSON com EXATAMENTE estas chaves:

episode_list
episode_link
player_button
blogger_regex
observacoes

HTML:
{html[:30000]}
"""

# =============================
# 3️⃣ CHAMADA À IA
# =============================

print("[IA] Analisando HTML completo...")

response = model.generate_content(prompt)
text = response.text.strip()

# =============================
# 4️⃣ PARSE JSON
# =============================

try:
    rules = extract_json(text)
    print("\n[IA] Regras geradas com sucesso:\n")
    print(json.dumps(rules, indent=2, ensure_ascii=False))

    os.makedirs("rules", exist_ok=True)
    with open("rules/goyabu.json", "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)

    print("\n[OK] Regras salvas em rules/goyabu.json")

except Exception as e:
    print("\n[ERRO] A IA não retornou JSON válido")
    print("Erro:", e)
    print("\nResposta bruta da IA:\n")
    print(text)
    raise
