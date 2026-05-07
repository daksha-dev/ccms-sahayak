from app.core.config import Settings
from app.schemas.dto import ActionPlanItem, ExtractionJSON
from app.services.llm_client import GeminiClient, load_prompt


async def generate_action_plan(extraction: ExtractionJSON, settings: Settings) -> list[ActionPlanItem]:
    prompt = load_prompt("action_plan_system.txt")
    payload = await GeminiClient(settings).json_completion(prompt, extraction.model_dump_json())
    if isinstance(payload, list):
        items = payload
    else:
        items = payload.get("action_plan_items", [])
    return [ActionPlanItem.model_validate(item) for item in items]


def action_summary(items: list[ActionPlanItem]) -> str:
    return " | ".join(f"{item.directive_type}: {item.recommended_action}" for item in items)
