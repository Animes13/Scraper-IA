import requests
import json
import os

# Pegando a chave do GitHub Secrets
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Defina a variável de ambiente GEMINI_API_KEY")

# Endpoint REST oficial do Gemini
GEMINI_URL = "https://gemini.googleapis.com/v1beta2/models/gemini-3-flash-preview:generateText"

# Prompt de teste
prompt = "Escreva um JSON simples com a chave 'teste' e valor 123. Retorne apenas JSON."

data = {
    "prompt": prompt,
    "temperature": 0,
    "maxOutputTokens": 100
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

try:
    response = requests.post(GEMINI_URL, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()

    # Extrai o texto gerado pelo modelo
    output_text = result.get("candidates", [{}])[0].get("output", "")
    print("Resposta bruta do Gemini:\n", output_text)

    # Tenta converter para JSON
    try:
        parsed = json.loads(output_text)
        print("\nJSON válido:\n", json.dumps(parsed, indent=2))
    except json.JSONDecodeError:
        print("\nNão é JSON válido:\n", output_text)

except requests.exceptions.RequestException as e:
    print("Erro na requisição:", e)
