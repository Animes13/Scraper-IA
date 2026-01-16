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
# FUNÇÃO: EXTRAI JSON
# =============================

def extract_json(text):
    clean = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    clean = clean.strip("` \n\t")
    return json.loads(clean)

# =============================
# 1️⃣ BAIXA HTML REAL (JS COMPLETO)
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
        # ESPERA CONTEÚDO REAL (ajuste se necessário)
        page.wait_for_selector("a", timeout=20000)
        page.wait_for_timeout(3000)
    except TimeoutError:
        print("[WARN] Nenhum seletor esperado encontrado, usando HTML atual")

    html = page.content()
    browser.close()

print(f"[OK] HTML final capturado ({len(html)} chars)")

# =============================
# DEBUG OPCIONAL
# =============================

if "<body" not in html.lower():
    raise RuntimeError("HTML inválido (sem body)")

# =============================
# 2️⃣ PROMPT IA (MELHORADO)
# =============================

prompt = f"""
Responda APENAS com JSON puro.

Você é uma IA especialista em scraping avançado.
Analise o HTML FINAL abaixo, que CONTÉM <head> E <body> completos,
renderizado por um navegador real com JavaScript executado.

NÃO presuma ausência de conteúdo.
Baseie-se EXCLUSIVAMENTE nos elementos realmente presentes no HTML.

Extraia informações MESMO QUE NÃO SEJAM ÓBVIAS.

Retorne EXATAMENTE estas chaves:

episode_list  -> seletor CSS do container de episódios
episode_link  -> seletor CSS do link de cada episódio
player_button -> seletor CSS do botão/link que leva ao player
blogger_regex -> regex de URL Blogger (ou null)
observacoes   -> explicação curta da lógica inferida

HTML:
{html[:40000]}
"""

# =============================
# 3️⃣ IA
# =============================

print("[IA] Analisando HTML completo...")

response = client.models.generate_content(
    model=model,
    contents=prompt
)

text = response.text.strip()

# =============================
# 4️⃣ PARSE JSON
# =============================

rules = extract_json(text)

print("\n[IA] Regras geradas com sucesso:\n")
print(json.dumps(rules, indent=2, ensure_ascii=False))

os.makedirs("rules", exist_ok=True)
with open("rules/goyabu.json", "w", encoding="utf-8") as f:
    json.dump(rules, f, indent=2, ensure_ascii=False)

print("\n[OK] Regras salvas em rules/goyabu.json")
