from __future__ import annotations

import html

import streamlit as st

from gauntlet_core import analyze_paper_text
from gauntlet_core.document_loader import SUPPORTED_EXTENSIONS, extract_text_from_bytes
from gauntlet_core.sample_text import SAMPLE_PAPER


st.set_page_config(page_title="The Gauntlet", page_icon="G", layout="wide")


CSS = """
<style>
:root {
  --gauntlet-ink: #17212b;
  --gauntlet-muted: #697586;
  --gauntlet-border: #d9e1e8;
  --gauntlet-teal: #0f766e;
  --gauntlet-amber: #b7791f;
  --gauntlet-red: #b42318;
}
.main .block-container {
  padding-top: 1.6rem;
  padding-bottom: 2rem;
  max-width: 1240px;
}
h1, h2, h3 {
  letter-spacing: 0;
}
.gauntlet-header {
  border-bottom: 1px solid var(--gauntlet-border);
  padding-bottom: 1rem;
  margin-bottom: 1.2rem;
}
.gauntlet-header h1 {
  color: var(--gauntlet-ink);
  font-size: 2.1rem;
  margin: 0;
}
.gauntlet-header p {
  color: var(--gauntlet-muted);
  margin: .25rem 0 0 0;
}
.verdict-panel {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  padding: 1.15rem;
  background: #ffffff;
}
.verdict-label {
  color: var(--gauntlet-muted);
  font-size: .82rem;
  text-transform: uppercase;
  letter-spacing: .08em;
}
.verdict-value {
  color: var(--gauntlet-ink);
  font-size: 2.2rem;
  font-weight: 760;
  margin-top: .1rem;
}
.finding-card {
  border: 1px solid var(--gauntlet-border);
  border-left: 4px solid var(--gauntlet-amber);
  border-radius: 8px;
  padding: .9rem 1rem;
  margin-bottom: .75rem;
  background: #ffffff;
}
.finding-card.high {
  border-left-color: var(--gauntlet-red);
}
.finding-card.low {
  border-left-color: var(--gauntlet-teal);
}
.finding-title {
  color: var(--gauntlet-ink);
  font-weight: 720;
  margin-bottom: .2rem;
}
.finding-meta {
  color: var(--gauntlet-muted);
  font-size: .84rem;
  margin-bottom: .55rem;
}
.finding-body {
  color: #293442;
  font-size: .95rem;
}
.muted-note {
  color: var(--gauntlet-muted);
  font-size: .92rem;
}
button[kind="primary"] {
  border-radius: 6px;
}
</style>
"""


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    render_header()
    left, right = st.columns([0.34, 0.66], gap="large")

    with left:
        render_upload_panel()

    with right:
        report = st.session_state.get("report")
        if report:
            render_report(report)
        else:
            render_empty_state()


def render_header() -> None:
    st.markdown(
        """
        <div class="gauntlet-header">
          <h1>The Gauntlet</h1>
          <p>Local rule-based paper review. Upload a paper and get a transparent verdict without an AI model or API key.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upload_panel() -> None:
    st.subheader("Upload paper")
    st.caption("Supported files: PDF, DOCX, TXT, and Markdown.")
    upload = st.file_uploader(
        "Choose a paper",
        type=[extension.lstrip(".") for extension in sorted(SUPPORTED_EXTENSIONS)],
        label_visibility="collapsed",
    )

    use_sample = st.toggle("Use built-in sample paper", value=False)

    analyze_clicked = st.button("Analyze Paper", type="primary", use_container_width=True)
    if analyze_clicked:
        try:
            if use_sample:
                report = analyze_paper_text(SAMPLE_PAPER, source_name="sample-paper.txt")
            elif upload is not None:
                text = extract_text_from_bytes(upload.name, upload.getvalue())
                if not text.strip():
                    st.error("No readable text was found in that file.")
                    return
                report = analyze_paper_text(text, source_name=upload.name)
            else:
                st.error("Upload a paper or turn on the sample paper first.")
                return
        except Exception as exc:  # Streamlit should show clean user-facing errors.
            st.error(str(exc))
            return
        st.session_state["report"] = report
        st.rerun()

    st.divider()
    st.markdown("**What the v1 rules check**")
    st.markdown(
        """
        - explicit resolution claims
        - mechanisms and missing gaps
        - internal contradictions
        - citation, math, data, and methodology markers
        """
    )
    st.info("This v1 does not call OpenAI, Anthropic, Gemini, Ollama, or any other AI provider.")


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="verdict-panel">
          <div class="verdict-label">Ready</div>
          <div class="verdict-value">Upload to begin</div>
          <p class="muted-note">The report will appear here with a verdict, confidence, claim breakdown, findings, and export options.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_report(report) -> None:
    st.markdown(
        f"""
        <div class="verdict-panel">
          <div class="verdict-label">Verdict</div>
          <div class="verdict-value">{html.escape(report.verdict)}</div>
          <p class="muted-note">{html.escape(report.summary)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Confidence", f"{report.confidence:.0%}")
    metric_cols[1].metric("Evidence quality", f"{report.evidence.score:.2f}/1.00")
    metric_cols[2].metric("Claims", len(report.claims))
    metric_cols[3].metric("Findings", len(report.findings))

    summary_tab, claims_tab, contradictions_tab, evidence_tab = st.tabs(
        ["Summary", "Claims", "Contradictions", "Evidence"]
    )

    with summary_tab:
        st.write(f"Source: `{report.source_name}`")
        st.write(f"Words: `{report.word_count}`")
        st.write(f"Sentences analyzed: `{report.sentence_count}`")
        st.write(
            f"Claim status: `{report.resolved_claims}` resolved, "
            f"`{report.partial_claims}` partial, `{report.failed_claims}` failed."
        )
        render_exports(report)

    with claims_tab:
        if not report.claims:
            st.warning("No explicit resolution claims were detected.")
        for claim in report.claims:
            st.markdown(f"**{claim.status.title()}** · quality `{claim.quality:.2f}`")
            st.write(claim.claim)
            st.caption(f"Mechanism: {claim.mechanism} | Gaps: {', '.join(claim.gaps) if claim.gaps else 'none'}")
            st.divider()

    with contradictions_tab:
        if not report.findings:
            st.success("No internal contradictions were detected by the v1 rules.")
        for finding in report.findings:
            render_finding(finding)

    with evidence_tab:
        st.progress(min(report.evidence.score, 1.0), text=f"Evidence quality {report.evidence.score:.2f}/1.00")
        evidence_cols = st.columns(5)
        evidence_cols[0].metric("Quantitative", report.evidence.quantitative_evidence)
        evidence_cols[1].metric("Math", report.evidence.mathematical_content)
        evidence_cols[2].metric("Citations", report.evidence.citations)
        evidence_cols[3].metric("Methodology", report.evidence.methodology_terms)
        evidence_cols[4].metric("Evidence terms", report.evidence.evidence_terms)


def render_exports(report) -> None:
    json_col, markdown_col = st.columns(2)
    json_col.download_button(
        "Export JSON",
        data=report.to_json(),
        file_name=f"{safe_stem(report.source_name)}-gauntlet-report.json",
        mime="application/json",
        use_container_width=True,
    )
    markdown_col.download_button(
        "Export Markdown",
        data=report.to_markdown(),
        file_name=f"{safe_stem(report.source_name)}-gauntlet-report.md",
        mime="text/markdown",
        use_container_width=True,
    )


def render_finding(finding) -> None:
    severity = html.escape(finding.severity)
    related = ""
    if finding.related_sentence:
        related = f"<p><strong>Related:</strong> {html.escape(finding.related_sentence)}</p>"
    st.markdown(
        f"""
        <div class="finding-card {severity}">
          <div class="finding-title">{html.escape(finding.type)}</div>
          <div class="finding-meta">Severity: {severity} | Confidence: {finding.confidence:.0%}</div>
          <div class="finding-body">
            <p>{html.escape(finding.sentence)}</p>
            {related}
            <p><strong>Why it matters:</strong> {html.escape(finding.explanation)}</p>
            <p><strong>Repair:</strong> {html.escape(finding.repair_suggestion)}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def safe_stem(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]
    cleaned = "".join(character if character.isalnum() or character in "-_" else "-" for character in stem)
    return cleaned.strip("-") or "paper"


if __name__ == "__main__":
    main()
