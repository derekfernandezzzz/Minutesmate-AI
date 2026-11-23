# MinutesMate AI

AI-powered meeting minutes and action-item accountability web application built with **Python**, **Streamlit**, **Google Gemini**, and **`python-docx`**.

## Overview
Meetings frequently generate important decisions and tasks, yet owners and deadlines often remain unclear once the call ends. **MinutesMate AI** turns raw meeting transcripts into structured meeting minutes, runs an accountability gap audit (calculating an Action-Item Clarity Score and drafting follow-up nudges), and exports outputs as Markdown (`.md`) or a formatted executive report (`.docx`).

## Key Features
- **Transcript Input & Sample Loader:** Enter a meeting title and date, paste a transcript, or load a sample transcript with one click.
- **Input Validation:** Rejects empty or overly short transcripts with clear error messages.
- **Structured Minutes & Accountability Audit:** Extracts a summary, key decisions, and action items (`Task`, `Owner`, `Deadline`), flags missing owners or deadlines (`Not specified`), computes a clarity score, and generates follow-up nudges.
- **Multi-Format Export:** Download results as Markdown (`.md`) or a styled corporate Word report (`.docx`).
- **Session Telemetry:** Sidebar tracks total runs, errors, and average response latency.

## Project Structure
- `app.py` — Streamlit UI, session telemetry, sample data loader, and report exports.
- `engine.py` — Input validation, Gemini API integration with model fallback, structured JSON parsing, and accountability audit logic.
- `tests/` — Automated `pytest` unit tests.
- `docs/idea_validation.md` — 7-step idea validation report and differentiating angle.
- `docs/PRD.md` — Product Requirements Document.
- `spec.md` — Technical specification and architecture notes.
- `CLAUDE.md` & `.cursorrules` — AI coding guidelines and project rules.
- `.github/workflows/ci.yml` — GitHub Actions CI workflow.

## Setup & Running Locally
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/derekfernandezzzz/Minutesmate-AI.git](https://github.com/derekfernandezzzz/Minutesmate-AI.git)
   cd Minutesmate-AI
