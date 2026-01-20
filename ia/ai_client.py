# ai/ai_client.py
import os
import json
import re
import asyncio
from typing import Dict, Any, Optional

from putergenai import PuterClient

# ------------------------------
# CONFIG
# ------------------------------
DEFAULT_MODEL_PRIORITY = [
    "gpt-5",
    "gpt-4o",
    "claude-opus-4.5",
    "gemini-pro",
    "gpt-5-nano",
]

MAX_RETRIES = 3


# ------------------------------
# AI CLIENT
# ------------------------------
class AIClient:
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.username = username or os.getenv("PUTER_USER")
        self.password = password or os.getenv("PUTER_PASS")

        if not self.username or not self.password:
            raise RuntimeError("Credenciais do Puter não configuradas")

        self.model = model
        self.client: Optional[PuterClient] = None

    # ------------------------------
    # CONTEXT MANAGER
    # ------------------------------
    async def __aenter__(self):
        self.client = PuterClient(auto_update_models=True)
        await self.client.__aenter__()
        await self.client.login(self.username, self.password)

        if not self.model:
            self.model = await self._select_best_model()

        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.client:
            await self.client.__aexit__(exc_type, exc, tb)

    # ------------------------------
    # MODEL SELECTION
    # ------------------------------
    async def _select_best_model(self) -> str:
        models_data = await self.client.get_available_models()
        available = set(self.client.get_model_list(models_data))

        for model in DEFAULT_MODEL_PRIORITY:
            if model in available:
                return model

        # fallback absoluto
        return next(iter(available))

    # ------------------------------
    # PROMPT BUILDER
    # ------------------------------
    def _build_prompt(self, ctx: Dict[str, Any]) -> str:
        anime = (ctx.get("anime") or "").replace("\n", " ")

        if ctx.get("stage") == "title_mapping":
            return f"""
Você é um assistente que busca títulos de animes no AniList.
NÃO invente dados.
Retorne APENAS JSON válido.

Anime: {anime}

Formato:

{{
  "type": "title_mapping",
  "confidence": 0.0,
  "rules": {{
    "title": "Título oficial"
  }}
}}
"""

        html = (ctx.get("html") or "").replace("“", '"').replace("”", '"')

        return f"""
Você é um analisador de HTML para scraping.
NÃO invente dados.
NÃO chute seletores.

Contexto:
Anime: {anime}
URL: {ctx.get("url")}
Etapa: {ctx.get("stage")}
Erro: {ctx.get("error_type")}

HTML:
{html}

Responda APENAS em JSON válido:

{{
  "type": "episode_list | selector_fix | title_mapping",
  "confidence": 0.0,
  "rules": {{
    "css": "...",
    "xpath": "...",
    "regex": "..."
  }}
}}
"""

    # ------------------------------
    # MAIN ANALYZE
    # ------------------------------
    async def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        last_error = None
        prompt = self._build_prompt(context)

        for _ in range(MAX_RETRIES):
            try:
                result = await self.client.ai_chat(
                    prompt=prompt,
                    options={
                        "model": self.model,
                        "temperature": 0.1,
                        "max_tokens": 1024,
                    },
                    strict_model=False,
                )

                text = self._extract_text(result)
                return self._safe_json(text)

            except Exception as e:
                last_error = str(e)

        raise RuntimeError(f"IA_FALHA: {last_error}")

    # ------------------------------
    # RESPONSE HANDLING
    # ------------------------------
    def _extract_text(self, result: Dict[str, Any]) -> str:
        try:
            return result["response"]["result"]["message"]["content"]
        except Exception:
            raise ValueError("Resposta inesperada da IA")

    # ------------------------------
    # JSON SAFE PARSE
    # ------------------------------
    def _safe_json(self, text: str) -> Dict[str, Any]:
        text = text.replace("“", '"').replace("”", '"').strip()

        text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
        text = re.sub(r"```$", "", text).strip()

        start = text.find("{")
        end = text.rfind("}") + 1

        if start == -1 or end == -1:
            raise ValueError(f"Resposta não contém JSON: {text}")

        try:
            return json.loads(text[start:end])
        except Exception as e:
            raise ValueError(f"JSON inválido: {e}\nRAW: {text}")