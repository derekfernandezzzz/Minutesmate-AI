# CLAUDE.md — Project Guidelines for AI Assistants

## Project Context
MinutesMate AI is a Python + Streamlit web application powered by the Google Gemini API (`google-genai`) that converts meeting transcripts into structured minutes and audits action items for missing owners and deadlines.

## Architecture & File Map
- `app.py`: Streamlit UI, session telemetry, sample data loader, and Markdown download.
- `engine.py`: Input validation, Gemini API integration, structured JSON parsing, and accountability gap audit logic.
- `tests/test_engine.py`: Pytest unit tests with mocked Gemini API calls.

## Rules for AI Code Generation
1. **Keep it modular and minimal:** Do not introduce unnecessary frameworks, databases, or bloated abstractions.
2. **Never hardcode secrets:** Always load `GEMINI_API_KEY` via environment variables (`os.getenv`) or Streamlit secrets.
3. **Strict grounding:** Prompt instructions must forbid inventing owners, deadlines, or decisions not present in the transcript; use `"Not specified"` when missing.
4. **Testable design:** Keep all LLM and business logic inside `engine.py` (never inside `app.py`) so `pytest` can test `engine.py` independently with mocks.
