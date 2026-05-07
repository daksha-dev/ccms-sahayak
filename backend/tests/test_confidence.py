from datetime import date

from app.services.confidence import appeal_deadline, overall_confidence, score_field, urgency_band


def test_confidence_source_matrix() -> None:
    assert score_field("WP No. 1 of 2024", "WP No. 1 of 2024") == (0.9, "BOTH", False)
    assert score_field(None, "High Court of Karnataka") == (0.7, "LLM", False)
    assert score_field("WP No. 1", "WA No. 2") == (0.35, "CONFLICT", True)
    assert score_field(None, None) == (0.0, "UNREADABLE", False)


def test_deadline_and_urgency_rules() -> None:
    deadline = appeal_deadline(date(2026, 5, 1), 30)
    assert deadline == date(2026, 5, 31)
    assert urgency_band(date(2026, 5, 8), "COMPLIANCE", today=date(2026, 5, 1)) == "RED"
    assert urgency_band(date(2026, 5, 20), "APPEAL", today=date(2026, 5, 1)) == "AMBER"
    assert urgency_band(None, "CONTEMPT", today=date(2026, 5, 1)) == "RED"
    assert urgency_band(date(2026, 7, 1), "COMPLIANCE", today=date(2026, 5, 1)) == "GREEN"


def test_overall_confidence_average() -> None:
    assert overall_confidence([0.9, 0.7, 0.35]) == 0.65
    assert overall_confidence([]) == 0.0
