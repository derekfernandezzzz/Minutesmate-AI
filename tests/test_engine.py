import json
from types import SimpleNamespace
import pytest
from engine import audit_action_items, generate_minutes, validate_transcript


class FakeModels:
    def __init__(self, payload_text: str):
        self._payload_text = payload_text

    def generate_content(self, model: str, contents: str, config: object) -> SimpleNamespace:
        return SimpleNamespace(text=self._payload_text)


class FakeClient:
    def __init__(self, payload_text: str):
        self.models = FakeModels(payload_text)


def test_validate_transcript_rejects_short_or_empty() -> None:
    with pytest.raises(ValueError):
        validate_transcript("")
    with pytest.raises(ValueError):
        validate_transcript("   too short   ")


def test_audit_action_items_flags_missing_owner_and_deadline() -> None:
    items = [
        {"task": "Send email template", "owner": "Maria", "deadline": "Wednesday"},
        {"task": "Fix billing webhook", "owner": "Devon", "deadline": "Not specified"},
        {"task": "Update FAQ page", "owner": "Not specified", "deadline": "Not specified"},
    ]
    result = audit_action_items(items)
    assert result["missing_count"] == 2
    assert result["clarity_score"] == 33
    assert result["audited_items"][2]["status"] == "Needs Clarification"


def test_generate_minutes_with_mocked_client() -> None:
    fake_payload = json.dumps(
        {
            "summary": "Team reviewed launch readiness and flagged open tasks.",
            "decisions": ["Launch with email notifications enabled by default."],
            "action_items": [
                {"task": "Update welcome email", "owner": "Maria", "deadline": "Wednesday"},
                {"task": "Update FAQ page", "owner": "Not specified", "deadline": "Not specified"},
            ],
            "followup_nudges": ["Ask who owns updating the FAQ page and set a deadline."],
        }
    )
    output = generate_minutes(
        transcript="We reviewed launch tasks today and assigned the welcome email update to Maria.",
        client=FakeClient(fake_payload),
    )
    assert output["clarity_score"] == 50
    assert output["missing_count"] == 1
    assert len(output["decisions"]) == 1
