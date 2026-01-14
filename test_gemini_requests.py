from google import genai
import json
import os

# Pega a chave do GitHub Secrets
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("A variável GEMINI_API_KEY não está definida")

client = genai.Client(api_key=API_KEY)

prompt = "Escreva um JSON simples com a chave 'teste' e valor 123. Retorne apenas JSON."

try:
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    output_text = response.text
    print("Resposta do Gemini:\n", output_text)

    try:
        parsed = json.loads(output_text)
        print("\nJSON válido:\n", json.dumps(parsed, indent=2))
    except json.JSONDecodeError:
        print("\nNão é JSON válido:\n", output_text)

except Exception as e:
    print("Erro ao chamar Gemini:", e)
