import json
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings


ROOT = Path(__file__).resolve().parents[3]


class GeminiClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        if not self.settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for Gemini Flash extraction and action planning.")
        return {"Authorization": f"Bearer {self.settings.openrouter_api_key}", "Content-Type": "application/json"}

    async def json_completion(self, system_prompt: str, user_content: str) -> Any:
        payload = {
            "model": self.settings.gemini_model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(self.settings.openrouter_url, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


def load_prompt(name: str) -> str:
    return (ROOT / "prompts" / name).read_text(encoding="utf-8")
