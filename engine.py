import json
import os
import time
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types

MODEL_ID = "gemini-4-hydrogen"
FALLBACK_MODEL_ID = "gemini-2.5-flash"


def validate_transcript(transcript: str) -> str:
    """Ensure the meeting transcript is non-empty and meaningful."""
    if not transcript or not isinstance(transcript, str):
        raise ValueError("Transcript cannot be empty.")
    cleaned = transcript.strip()
    if len(cleaned) < 20:
        raise ValueError("Transcript is too short. Please paste at least 20 characters.")
    return cleaned


def audit_action_items(action_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Flag missing owners/deadlines and compute a 0-100% Meeting Clarity Score."""
    if not action_items:
        return {
            "audited_items": [],
            "clarity_score": 100,
            "missing_count": 0,
        }

    audited: List[Dict[str, Any]] = []
    missing_count = 0

    for item in action_items:
        task = str(item.get("task", "")).strip() or "Unspecified task"
        owner = str(item.get("owner", "")).strip() or "Not specified"
        deadline = str(item.get("deadline", "")).strip() or "Not specified"

        missing_owner = owner.lower() in {"", "not specified", "none", "tbd", "n/a", "unassigned"}
        missing_deadline = deadline.lower() in {"", "not specified", "none", "tbd", "n/a", "soon"}

        gaps: List[str] = []
        if missing_owner:
            owner = "Not specified"
            gaps.append("Missing Owner")
        if missing_deadline:
            deadline = "Not specified"
            gaps.append("Missing Deadline")

        if gaps:
            missing_count += 1

        audited.append(
            {
                "task": task,
                "owner": owner,
                "deadline": deadline,
                "status": "Needs Clarification" if gaps else "Clear",
                "gaps": ", ".join(gaps) if gaps else "Complete",
            }
        )

    total = len(audited)
    clear_count = total - missing_count
    clarity_score = round((clear_count / total) * 100)

    return {
        "audited_items": audited,
        "clarity_score": clarity_score,
        "missing_count": missing_count,
    }


def generate_minutes(
    transcript: str,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Generate structured meeting minutes and run accountability audit."""
    cleaned_transcript = validate_transcript(transcript)

    if client is None:
        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        if not resolved_key:
            raise ValueError("Missing GEMINI_API_KEY. Please configure it in secrets.")
        client = genai.Client(api_key=resolved_key)

    prompt = f"""
You are MinutesMate AI, a strict workplace meeting minutes and accountability assistant.
Analyze the meeting transcript below and extract ONLY facts explicitly stated in the text.
Do NOT invent or guess owners, deadlines, or decisions. If an owner or deadline is not stated, set it to "Not specified".

Return valid JSON matching this exact structure:
{{
  "summary": "2-3 sentence executive summary of the meeting",
  "decisions": ["Decision 1", "Decision 2"],
  "action_items": [
    {{
      "task": "Actionable task description",
      "owner": "Person responsible or 'Not specified'",
      "deadline": "Stated deadline or 'Not specified'"
    }}
  ],
  "followup_nudges": [
    "Short, polite follow-up message to clarify missing owners/deadlines or confirm key tasks"
  ]
}}

Transcript:
\"\"\"
{cleaned_transcript}
\"\"\"
"""

    start_time = time.perf_counter()
    models_to_try = [MODEL_ID, FALLBACK_MODEL_ID]
    response = None
    last_exc: Optional[Exception] = None
    model_used = MODEL_ID

    for candidate_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=candidate_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            model_used = candidate_model
            break
        except Exception as exc:
            last_exc = exc
            if "503" in str(exc) or "UNAVAILABLE" in str(exc):
                continue
            raise

    if response is None and last_exc is not None:
        raise last_exc

    latency_sec = round(time.perf_counter() - start_time, 2)

    raw_text = (response.text or "").strip()
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("AI returned invalid JSON. Please try again.") from exc

    audit = audit_action_items(parsed.get("action_items", []))

    return {
        "summary": parsed.get("summary", "No summary generated."),
        "decisions": parsed.get("decisions", []),
        "action_items": audit["audited_items"],
        "clarity_score": audit["clarity_score"],
        "missing_count": audit["missing_count"],
        "followup_nudges": parsed.get("followup_nudges", []),
        "latency_sec": latency_sec,
        "model_used": model_used,
    }
