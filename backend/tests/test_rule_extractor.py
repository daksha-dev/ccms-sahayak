from datetime import date

from app.services.rule_extractor import extract_case_number, extract_court_name, extract_order_date


def test_rule_extracts_case_number() -> None:
    text = "IN THE HIGH COURT OF KARNATAKA\nW.P. No. 1234 of 2024\nBetween"
    assert extract_case_number(text) == "W.P. No. 1234 of 2024"


def test_rule_extracts_karnataka_high_court() -> None:
    assert extract_court_name("IN THE HIGH COURT OF KARNATAKA AT BENGALURU") == "High Court of Karnataka"


def test_rule_extracts_order_date() -> None:
    text = "DATED THIS THE 5th DAY OF MAY, 2026"
    assert extract_order_date(text) == date(2026, 5, 5)
