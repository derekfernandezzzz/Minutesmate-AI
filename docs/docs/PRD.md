# Product Requirements Document (PRD) — MinutesMate AI

## 1. Product Overview
MinutesMate AI is a web application that converts raw meeting transcripts into structured meeting minutes and audits action items for missing owners and deadlines.

## 2. Target Users
- Project Managers & Team Leads tracking deliverables across recurring meetings.
- Administrative Staff & Coordinators responsible for distributing official meeting summaries.

## 3. Core Functional Requirements (MVP)
- **FR-1 Transcript Input & Sample Loader:** Users can enter a meeting title, date, and paste a transcript, or load a built-in sample transcript with one click.
- **FR-2 Input Validation:** System prevents empty or overly short inputs and displays clear error messages.
- **FR-3 Structured Minutes Generation:** AI extracts an Executive Summary, Key Decisions Made, and Action Items (Task, Owner, Deadline).
- **FR-4 Accountability Audit (Differentiator):** System flags action items where Owner or Deadline is missing (`Not specified`), computes a Meeting Clarity Score, and generates copy-ready follow-up nudges.
- **FR-5 Export:** Users can download the formatted minutes as a `.md` (Markdown) file.
- **FR-6 Basic Monitoring:** Sidebar displays live session telemetry (total runs, average response latency, and error count).

## 4. Non-Goals (Out of Scope for v1)
- Live meeting bot integrations (Zoom/Teams) or audio file transcription (planned for v2).
- User authentication or real payment processing.

## 5. Success Metrics
- Generates structured output in < 10 seconds per transcript.
- 100% of extracted fields grounded strictly in the provided transcript (no invented names or dates).
