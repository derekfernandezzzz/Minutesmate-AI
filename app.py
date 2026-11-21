from datetime import date
from io import BytesIO
import os
from typing import Any, Dict, List

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor
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


def _set_cell_shading(cell, hex_color: str) -> None:
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _set_cell_margins(cell, top: int = 100, bottom: int = 100, left: int = 140, right: int = 140) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def _set_table_borders(table, color: str = "D8DEE9", sz: str = "4") -> None:
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/><w:right w:val="none"/><w:insideV w:val="none"/>'
        f"</w:tblBorders>"
    )
    tblPr.append(borders)


def _add_section_heading(doc: Document, title: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(title.upper())
    run.font.name = "Calibri"
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x0F, 0x29, 0x4A)

    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'<w:bottom w:val="single" w:sz="8" w:space="3" w:color="1E4E8C"/>'
        f"</w:pBdr>"
    )
    pPr.append(pBdr)


def build_corporate_docx(meeting_title: str, meeting_date: str, data: Dict[str, Any]) -> bytes:
    """Render meeting minutes and accountability audit into a corporate Word (.docx) document."""
    clean_title = (meeting_title or "").strip() or "Executive Meeting Minutes"
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
        section.different_first_page_header_footer = True

        hdr = section.header
        hp = hdr.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run(f"{clean_title}  |  {meeting_date}")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

        ftr = section.footer
        fp = ftr.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        frun = fp.add_run("Prepared with MinutesMate AI  •  Internal & Executive Distribution")
        frun.font.name = "Calibri"
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    banner = doc.add_table(rows=1, cols=1)
    banner.alignment = WD_TABLE_ALIGNMENT.CENTER
    bcell = banner.cell(0, 0)
    bcell.width = Inches(6.9)
    _set_cell_shading(bcell, "0F294A")
    _set_cell_margins(bcell, top=180, bottom=180, left=220, right=220)

    bp1 = bcell.paragraphs[0]
    bp1.paragraph_format.space_before = Pt(0)
    bp1.paragraph_format.space_after = Pt(2)
    kicker = bp1.add_run("MEETING MINUTES & ACCOUNTABILITY BRIEF")
    kicker.font.name = "Calibri"
    kicker.font.size = Pt(8.5)
    kicker.font.bold = True
    kicker.font.color.rgb = RGBColor(0x93, 0xC5, 0xFD)

    bp2 = bcell.add_paragraph()
    bp2.paragraph_format.space_before = Pt(0)
    bp2.paragraph_format.space_after = Pt(0)
    title_run = bp2.add_run(clean_title)
    title_run.font.name = "Calibri"
    title_run.font.size = Pt(18)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    score = data.get("clarity_score", 0)
    missing = data.get("missing_count", 0)

    meta_tbl = doc.add_table(rows=1, cols=3)
    meta_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(meta_tbl, color="CBD5E1", sz="4")
    col_widths = [Inches(2.3), Inches(2.3), Inches(2.3)]
    meta_cards = [
        ("MEETING DATE", str(meeting_date), "0F172A"),
        ("CLARITY SCORE", f"{score}%", "15803D" if score >= 75 else "B45309"),
        ("ACTION GAPS", f"{missing} item(s) flagged", "B91C1C" if missing > 0 else "15803D"),
    ]
    for idx, (label, val, hex_col) in enumerate(meta_cards):
        c = meta_tbl.cell(0, idx)
        c.width = col_widths[idx]
        _set_cell_shading(c, "F8FAFC")
        _set_cell_margins(c, top=110, bottom=110, left=140, right=140)
        p_lbl = c.paragraphs[0]
        p_lbl.paragraph_format.space_before = Pt(0)
        p_lbl.paragraph_format.space_after = Pt(2)
        r_lbl = p_lbl.add_run(label)
        r_lbl.font.name = "Calibri"
        r_lbl.font.size = Pt(7.5)
        r_lbl.font.bold = True
        r_lbl.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

        p_val = c.add_paragraph()
        p_val.paragraph_format.space_before = Pt(0)
        p_val.paragraph_format.space_after = Pt(0)
        r_val = p_val.add_run(val)
        r_val.font.name = "Calibri"
        r_val.font.size = Pt(12)
        r_val.font.bold = True
        r_val.font.color.rgb = RGBColor.from_string(hex_col)

    _add_section_heading(doc, "Executive Summary")
    p_sum = doc.add_paragraph(str(data.get("summary", "")))
    p_sum.paragraph_format.space_before = Pt(2)
    p_sum.paragraph_format.space_after = Pt(8)
    p_sum.paragraph_format.line_spacing = 1.15
    for r in p_sum.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(10.5)
        r.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    _add_section_heading(doc, "Key Decisions")
    decisions = data.get("decisions", [])
    if decisions:
        for d in decisions:
            p_dec = doc.add_paragraph(style="List Bullet")
            p_dec.paragraph_format.space_before = Pt(1)
            p_dec.paragraph_format.space_after = Pt(4)
            p_dec.paragraph_format.line_spacing = 1.15
            run = p_dec.add_run(str(d))
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    else:
        p_none = doc.add_paragraph("No explicit decisions recorded.")
        p_none.runs[0].font.italic = True
        p_none.runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    _add_section_heading(doc, "Action Items & Accountability Audit")
    items = data.get("action_items", [])
    if items:
        headers = ["Action Item", "Owner", "Deadline", "Audit Status"]
        widths = [Inches(3.1), Inches(1.25), Inches(1.25), Inches(1.3)]
        tbl = doc.add_table(rows=1, cols=4)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(tbl, color="CBD5E1", sz="4")

        hdr_cells = tbl.rows[0].cells
        for i, h_text in enumerate(headers):
            hdr_cells[i].width = widths[i]
            hdr_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            _set_cell_shading(hdr_cells[i], "1E3A5F")
            _set_cell_margins(hdr_cells[i], top=100, bottom=100, left=110, right=110)
            p = hdr_cells[i].paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(h_text)
            r.font.name = "Calibri"
            r.font.size = Pt(9.5)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        for row_idx, item in enumerate(items):
            row_cells = tbl.add_row().cells
            bg_hex = "FFFFFF" if row_idx % 2 == 0 else "F8FAFC"
            task_txt = str(item.get("task", ""))
            owner_txt = str(item.get("owner", "Not specified"))
            deadline_txt = str(item.get("deadline", "Not specified"))
            status_txt = str(item.get("status", "Clear"))

            vals = [task_txt, owner_txt, deadline_txt, status_txt]
            needs_clarification = any(w in status_txt.lower() for w in ("clarif", "gap", "missing"))

            for i, val in enumerate(vals):
                row_cells[i].width = widths[i]
                row_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                cell_bg = "FEF2F2" if (i == 3 and needs_clarification) else bg_hex
                _set_cell_shading(row_cells[i], cell_bg)
                _set_cell_margins(row_cells[i], top=90, bottom=90, left=110, right=110)
                p = row_cells[i].paragraphs[0]
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(val)
                r.font.name = "Calibri"
                r.font.size = Pt(9.5)
                if i == 3 and needs_clarification:
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(0xB9, 0x1C, 0x1C)
                elif i == 3:
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(0x15, 0x80, 0x3D)
                else:
                    r.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    else:
        p_no_act = doc.add_paragraph("No action items identified.")
        p_no_act.runs[0].font.italic = True
        p_no_act.runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    _add_section_heading(doc, "Suggested Follow-Up Nudges")
    nudges = data.get("followup_nudges", [])
    if nudges:
        for n in nudges:
            p_nudge = doc.add_paragraph(style="List Bullet")
            p_nudge.paragraph_format.space_before = Pt(1)
            p_nudge.paragraph_format.space_after = Pt(4)
            p_nudge.paragraph_format.line_spacing = 1.15
            run = p_nudge.add_run(str(n))
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    else:
        p_ok = doc.add_paragraph("All action items have clear owners and deadlines.")
        p_ok.runs[0].font.italic = True
        p_ok.runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


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

            nd_text = build_markdown_export(meeting_title, meeting_date, data)
            st.download_button(
                label="Download Minutes (.md)",
                data=nd_text,
                file_name="meeting_minutes.md",
                mime="text/markdown",
            )

            docx_bytes = build_corporate_docx(meeting_title, meeting_date, data)
            safe_slug = (
                "".join(c if c.isalnum() or c in (" ", "_", "-") else "" for c in (meeting_title or "meeting_minutes"))
                .strip()
                .lower()
                .replace(" ", "_")
                or "meeting_minutes"
            )
            st.download_button(
                label="Download Executive Report (.docx)",
                data=docx_bytes,
                file_name=f"{safe_slug}_executive.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )


if __name__ == "__main__":
    main()
