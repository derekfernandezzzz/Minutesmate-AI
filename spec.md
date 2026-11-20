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
