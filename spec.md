# Technical Specification & Architecture — MinutesMate AI

## 1. Architecture Overview
MinutesMate AI uses a clean 2-layer Python web architecture deployed on Streamlit Community Cloud:
- **Presentation & Monitoring Layer (`app.py`):** Streamlit web UI handling user inputs, sample transcript loading, result rendering, Markdown export, and lightweight in-memory analytics (run count, latency, errors).
- **AI Intelligence & Audit Layer (`engine.py`):** Validates input text, invokes Google Gemini (`gemini-3.8-flash`) with strict JSON schema instructions, runs deterministic gap-detection rules on extracted action items, and computes a Meeting Clarity Score.

## 2. Data Flow
`User Transcript` -> `Input Validator` -> `Gemini API (Structured JSON)` -> `Accountability Gap Auditor` -> `UI Display + .md Export`

## 3. JSON Output Contract
```json
{
  "summary": "string",
  "decisions": ["string"],
  "action_items": [
    {
      "task": "string",
      "owner": "string or 'Not specified'",
      "deadline": "string or 'Not specified'"
    }
  ],
  "followup_nudges": ["string"]
}
## Architecture Notes & Post-Review Revisions
- **System Flow:** Streamlit UI (`app.py`) validates transcript input (`validate_transcript`), calls `generate_minutes` in `engine.py` via the Google Gemini SDK using structured JSON output, runs `audit_action_items` to compute the 0–100% Action-Item Clarity Score and follow-up nudges, and updates session telemetry (`Runs`, `Errors`, `Avg Latency`).
- **Model Resilience (Post-Review Revision):** Added automatic fallback from `gemini-4-hydrogen` to `gemini-3.8-flash` on transient `503 UNAVAILABLE` / demand spikes so live demo runs remain reliable.
- **v1 Scope Boundary:** Kept audio file uploads out of v1 and standardized on text transcripts + Markdown export to keep latency and reliability predictable.
