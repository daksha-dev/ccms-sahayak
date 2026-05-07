from datetime import date, timedelta
from typing import Any


HIGH = 0.9
MEDIUM = 0.7
LOW = 0.35
UNREADABLE = 0.0


def score_field(rule_value: Any, llm_value: Any) -> tuple[float, str, bool]:
    if rule_value not in (None, "", []) and llm_value not in (None, "", []):
        if str(rule_value).strip().lower() == str(llm_value).strip().lower():
            return HIGH, "BOTH", False
        return LOW, "CONFLICT", True
    if llm_value not in (None, "", []):
        return MEDIUM, "LLM", False
    if rule_value not in (None, "", []):
        return HIGH, "RULE", False
    return UNREADABLE, "UNREADABLE", False


def overall_confidence(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 3)


def appeal_deadline(order_date: date | None, limitation_days: int | None) -> date | None:
    if not order_date or limitation_days is None:
        return None
    return order_date + timedelta(days=limitation_days)


def urgency_band(deadline: date | None, directive_type: str | None, today: date | None = None) -> str:
    if directive_type == "CONTEMPT":
        return "RED"
    if not deadline:
        return "GREEN"
    days = (deadline - (today or date.today())).days
    if days <= 7:
        return "RED"
    if days <= 30 or directive_type == "APPEAL":
        return "AMBER"
    return "GREEN"
