"""P1-13: Streamlit UI for ITFDS pipeline."""
from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import streamlit as st

from app.pipeline import run_pipeline
from app.state import PipelineState

st.set_page_config(page_title="ITFDS", page_icon="🏦", layout="wide")

st.title("Intelligent Trade Finance Document System")
st.caption("Upload a trade bundle folder (zipped) to run the full compliance pipeline.")

# ── Session state ─────────────────────────────────────────────────────────────
if "last_state" not in st.session_state:
    st.session_state.last_state = None
if "last_run_dir" not in st.session_state:
    st.session_state.last_run_dir = None


# ── Upload ────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload trade bundle (.zip containing manifest.yaml + PDFs)",
    type=["zip"],
)

run_btn = st.button("Run Pipeline", type="primary", disabled=uploaded is None)

if run_btn and uploaded:
    with st.spinner("Running pipeline A → B → C → D → E → H …"):
        # Extract zip into temp dir
        tmp_root = Path(tempfile.mkdtemp())
        zip_path = tmp_root / uploaded.name
        zip_path.write_bytes(uploaded.getvalue())

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_root / "bundle")

        # Find the bundle dir (first subdir or root)
        bundle_path = tmp_root / "bundle"
        subdirs = [p for p in bundle_path.iterdir() if p.is_dir()]
        if subdirs:
            bundle_path = subdirs[0]

        run_dir = tmp_root / "run"
        run_dir.mkdir()

        bundle_id = bundle_path.name or uploaded.name.replace(".zip", "")

        state = PipelineState(
            bundle_id=bundle_id,
            bundle_path=bundle_path,
            run_dir=run_dir,
        )

        try:
            state = run_pipeline(state)
            st.session_state.last_state = state
            st.session_state.last_run_dir = run_dir
        except Exception as exc:
            st.error(f"Pipeline error: {exc}")
            state = None

# ── Results ───────────────────────────────────────────────────────────────────
state: PipelineState | None = st.session_state.last_state
run_dir: Path | None = st.session_state.last_run_dir

if state is not None:
    st.divider()

    # Decision banner
    decision = state.final_decision.decision if state.final_decision else "PENDING"
    color = {"HONOUR": "green", "REFUSE": "red", "ESCALATE": "orange"}.get(decision, "blue")
    st.markdown(f"## :{color}[Decision: {decision}]")

    if state.final_decision:
        fd = state.final_decision
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Major findings", fd.findings_summary.major)
        col2.metric("Minor findings", fd.findings_summary.minor)
        col3.metric("Warnings", fd.findings_summary.warnings)
        col4.metric("Sanctions hits", fd.findings_summary.sanctions_hits)
        st.caption(f"Basis: {fd.decision_basis}")

    # Warnings / errors
    if state.warnings:
        with st.expander(f"⚠️ Warnings ({len(state.warnings)})"):
            for w in state.warnings:
                st.write(f"- {w}")
    if state.errors:
        with st.expander(f"❌ Errors ({len(state.errors)})"):
            for e in state.errors:
                st.write(f"- {e}")

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_match, tab_extract, tab_ucp, tab_sanctions, tab_artifacts = st.tabs([
        "Matching", "Extraction", "UCP 600", "Sanctions", "Download Artifacts",
    ])

    with tab_match:
        if state.match_result:
            st.subheader("Cross-Document Consistency")
            for c in state.match_result.comparisons:
                icon = "✅" if c.match else ("🔴" if c.severity.value == "major" else "🟡")
                with st.expander(f"{icon} {c.field_name} — {c.severity.value.upper()}"):
                    for v in c.values:
                        st.write(f"**{v.document}:** {v.value}")
                    if c.notes:
                        st.caption(c.notes)
        else:
            st.info("No matching result.")

    with tab_extract:
        if state.extracted:
            st.subheader("Extracted Fields")
            for doc in state.extracted.documents:
                with st.expander(f"📄 {doc.document_type.value} — {doc.file}"):
                    rows = []
                    for f in doc.fields:
                        rows.append({
                            "Field": f.field_name,
                            "Value": f.value or "—",
                            "Confidence": f"{f.confidence:.0%}",
                            "Low confidence": "⚠️" if f.low_confidence else "",
                            "LLM derived": "🤖" if f.llm_derived else "",
                        })
                    if rows:
                        st.table(rows)
        else:
            st.info("No extraction result.")

    with tab_ucp:
        if state.ucp_result:
            st.subheader("UCP 600 Checks")
            ucp = state.ucp_result
            col1, col2, col3 = st.columns(3)
            col1.metric("Rules checked", ucp.rules_checked)
            col2.metric("Passed", ucp.rules_passed)
            col3.metric("Failed", ucp.rules_failed)
            for r in ucp.results:
                icon = "✅" if r.passed else ("🔴" if r.severity.value == "major" else "🟡")
                st.write(f"{icon} **{r.rule_id}** — {r.rule_name}")
        else:
            st.info("No UCP result.")

    with tab_sanctions:
        if state.sanctions:
            sc = state.sanctions
            status_icon = "🔴" if sc.overall_status == "HIT" else "✅"
            st.metric("Sanctions status", f"{status_icon} {sc.overall_status}")
            if sc.hits:
                for hit in sc.hits:
                    st.warning(f"**{hit.list_name}** — {hit.matched_name} (score: {hit.match_score:.0%})")
            else:
                st.success("No sanctions hits.")
        else:
            st.info("No sanctions result.")

    with tab_artifacts:
        st.subheader("Download Artifacts")
        if run_dir and run_dir.exists():
            artifact_map = {
                "extracted_docs.csv": "📊 Extracted Fields (CSV)",
                "match_result.json": "🔍 Match Result (JSON)",
                "final_decision.json": "⚖️ Final Decision (JSON)",
                "swift_draft.txt": "📨 SWIFT Draft (TXT)",
                "discrepancies.md": "📋 Discrepancies (Markdown)",
                "ucp_result.json": "📜 UCP Result (JSON)",
                "sanctions_screen.json": "🛡️ Sanctions Screen (JSON)",
            }
            for filename, label in artifact_map.items():
                fpath = run_dir / filename
                if fpath.exists():
                    st.download_button(
                        label=label,
                        data=fpath.read_bytes(),
                        file_name=filename,
                        key=filename,
                    )
        else:
            st.info("No artifacts available.")
