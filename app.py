import os
from datetime import date
from typing import Any, Dict, List
import streamlit as st
from engine import MODEL_ID, generate_minutes

SAMPLE_TRANSCRIPT = """Meeting: Weekly Product & Operations Sync
Alex: Let's review the onboarding checklist before Friday's launch.
Maria: I can update the welcome email template and send it for review by Wednesday afternoon.
Alex: Great. What about the billing webhook bug?
Devon: I'm looking into it, not sure when I'll have a fix yet.
Alex: Okay, let's also make sure someone updates the FAQ page. We decided to launch with email notifications enabled by default."""


def get_api_key() -> str:
    """Retrieve GEMINI_API_KEY from Streamlit secrets or environment variables."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"])
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "")


def init_state() -> None:
    """Initialize session state for inputs, outputs, and basic telemetry."""
    if "transcript_input" not in st.session_state:
        st.session_state.transcript_input = ""
    if "result" not in st.session_state:
        st.session_state.result = None
    if "total_runs" not in st.session_state:
        st.session_state.total_runs = 0
    if "error_count" not in st.session_state:
        st.session_state.error_count = 0
    if "latencies" not in st.session_state:
        st.session_state.latencies: List[float] = []


def build_markdown_export(title: str, meeting_date: str, data: Dict[str, Any]) -> str:
    """Format meeting minutes and accountability audit into clean Markdown."""
    lines = [
        f"# Meeting Minutes: {title or 'Untitled Meeting'}",
        f"**Date:** {meeting_date}",
        f"**Action-Item Clarity Score:** {data.get('clarity_score', 0)}%",
        "",
        "## Executive Summary",
        data.get("summary", ""),
        "",
        "## Decisions Made",
    ]
    decisions = data.get("decisions", [])
    if decisions:
        for d in decisions:
            lines.append(f"- {d}")
    else:
        lines.append("- None explicitly recorded.")

    lines.extend(["", "## Action Items & Accountability Audit"])
    items = data.get("action_items", [])
    if items:
        for item in items:
            lines.append(
                f"- **{item.get('task')}** | Owner: `{item.get('owner')}` | "
                f"Deadline: `{item.get('deadline')}` | Status: `{item.get('status')}`"
            )
    else:
        lines.append("- No action items extracted.")

    lines.extend(["", "## Follow-Up Nudges"])
    nudges = data.get("followup_nudges", [])
    if nudges:
        for n in nudges:
            lines.append(f"- {n}")
    else:
        lines.append("- No follow-up nudges needed.")

    return "\n".join(lines)


def main() -> None:
    st.set_page_config(
        page_title="MinutesMate AI",
        page_icon="📝",
        layout="wide",
    )
    init_state()

    st.title("📝 MinutesMate AI")
    st.caption(
        "Turn meeting transcripts into structured minutes—and catch missing owners or deadlines before tasks slip."
    )

    with st.sidebar:
        st.header("Session Telemetry")
        avg_latency = (
            round(sum(st.session_state.latencies) / len(st.session_state.latencies), 2)
            if st.session_state.latencies
            else 0.0
        )
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Runs", st.session_state.total_runs)
        col_m2.metric("Errors", st.session_state.error_count)
        st.metric("Avg Latency (s)", avg_latency)
        st.caption(f"Model: `{MODEL_ID}`")

    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.subheader("1. Meeting Input")
        meeting_title = st.text_input("Meeting Title", placeholder="e.g., Weekly Product Sync")
        meeting_date = str(st.date_input("Meeting Date", value=date.today()))

        if st.button("Load Sample Transcript"):
            st.session_state.transcript_input = SAMPLE_TRANSCRIPT
            st.rerun()

        transcript = st.text_area(
            "Meeting Transcript",
            key="transcript_input",
            height=240,
            placeholder="Paste your meeting transcript here...",
        )

        generate_clicked = st.button("Generate Minutes", type="primary")

        if generate_clicked:
            api_key = get_api_key()
            if not api_key:
                st.session_state.error_count += 1
                st.error("GEMINI_API_KEY is missing. Add it to Streamlit Secrets or environment variables.")
            else:
                try:
                    with st.spinner("Analyzing transcript and auditing action items..."):
                        output = generate_minutes(transcript=transcript, api_key=api_key)
                    st.session_state.result = output
                    st.session_state.total_runs += 1
                    st.session_state.latencies.append(float(output.get("latency_sec", 0.0)))
                except Exception as exc:
                    st.session_state.error_count += 1
                    st.error(f"Could not generate minutes: {exc}")

    with col_right:
        st.subheader("2. Minutes & Accountability Audit")
        data = st.session_state.result
        if not data:
            st.info("Paste a transcript on the left (or click 'Load Sample Transcript') and click Generate Minutes.")
        else:
            score = data.get("clarity_score", 0)
            missing = data.get("missing_count", 0)
            st.metric("Action-Item Clarity Score", f"{score}%", delta=f"{missing} item(s) with gaps", delta_color="inverse")

            st.markdown("### Summary")
            st.write(data.get("summary", ""))

            st.markdown("### Key Decisions")
            decisions = data.get("decisions", [])
            if decisions:
                for d in decisions:
                    st.markdown(f"- {d}")
            else:
                st.caption("No explicit decisions found.")

            st.markdown("### Action Items & Gap Audit")
            items = data.get("action_items", [])
            if items:
                st.dataframe(items, use_container_width=True)
            else:
                st.caption("No action items found.")

            st.markdown("### Suggested Follow-Up Nudges")
            nudges = data.get("followup_nudges", [])
            if nudges:
                for n in nudges:
                    st.markdown(f"- {n}")
            else:
                st.caption("All action items look clear.")

            md_text = build_markdown_export(meeting_title, meeting_date, data)
            st.download_button(
                label="Download Minutes (.md)",
                data=md_text,
                file_name="meeting_minutes.md",
                mime="text/markdown",
            )


if __name__ == "__main__":
    main()
