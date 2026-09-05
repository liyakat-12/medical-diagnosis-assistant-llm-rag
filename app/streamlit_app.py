"""
Streamlit chat UI for the Medical Diagnosis Assistant.

Run with:
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import html
import re
import sys
import textwrap
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from src import config
from src.pipeline.rag_pipeline import run_pipeline

st.set_page_config(
    page_title="Diagnosis Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

EXAMPLE_QUERIES = [
    {
        "title": "Cold symptoms",
        "text": "I have a runny nose and sore throat for two days",
        "hint": "Typical self-care case",
    },
    {
        "title": "Urinary discomfort",
        "text": "Burning when I pee and I need to go often",
        "hint": "May need a doctor visit",
    },
    {
        "title": "Chest pain",
        "text": "Sudden crushing chest pain and shortness of breath",
        "hint": "Emergency red-flag check",
    },
    {
        "title": "One-sided headache",
        "text": "Throbbing headache on one side with nausea and light sensitivity",
        "hint": "Cited differential",
    },
]

TRIAGE_META = {
    "self_care": {
        "tone": "self",
        "badge": "Self-care",
        "icon": "●",
    },
    "consult_doctor": {
        "tone": "consult",
        "badge": "See a clinician",
        "icon": "●",
    },
    "emergency": {
        "tone": "emergency",
        "badge": "Emergency care",
        "icon": "●",
    },
}

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
  font-family: "Source Sans 3", "Segoe UI", sans-serif;
}

.stApp {
  background:
    radial-gradient(1200px 500px at 12% -10%, rgba(45, 212, 191, 0.10), transparent 55%),
    radial-gradient(900px 420px at 100% 0%, rgba(56, 189, 248, 0.06), transparent 50%),
    #0b1220;
  color: #e8eef7;
}

header[data-testid="stHeader"],
div[data-testid="stDecoration"],
div[data-testid="stToolbar"],
div[data-testid="stStatusWidget"],
.stDeployButton,
#MainMenu,
footer {
  display: none !important;
  visibility: hidden;
}

.block-container {
  padding-top: 1.4rem;
  padding-bottom: 6.5rem;
  max-width: 1080px;
}

section[data-testid="stSidebar"] {
  background: #0d1524 !important;
  border-right: 1px solid rgba(148, 163, 184, 0.12);
}

section[data-testid="stSidebar"] > div {
  padding-top: 1.2rem;
}

section[data-testid="stSidebar"] .stMarkdown p {
  color: #cbd5e1;
}

.brand {
  display: flex;
  gap: 0.85rem;
  align-items: center;
  margin-bottom: 1.35rem;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.25rem;
  background: linear-gradient(160deg, #2dd4bf, #0ea5e9);
  box-shadow: 0 8px 24px rgba(45, 212, 191, 0.25);
}

.brand h1 {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  margin: 0;
  color: #f8fafc;
}

.brand p {
  margin: 0.1rem 0 0;
  font-size: 0.78rem;
  color: #94a3b8;
}

.hero {
  text-align: center;
  padding: 2.4rem 1rem 1.4rem;
}

.hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  background: rgba(45, 212, 191, 0.10);
  border: 1px solid rgba(45, 212, 191, 0.22);
  color: #5eead4;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero h2 {
  margin: 0.9rem 0 0.45rem;
  font-size: 2.15rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: #f8fafc;
}

.hero p {
  margin: 0 auto;
  max-width: 560px;
  color: #94a3b8;
  font-size: 1.02rem;
  line-height: 1.55;
}

.status-grid {
  display: grid;
  gap: 0.65rem;
  margin: 0.2rem 0 1rem;
}

.status-card {
  background: #121a2b;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  padding: 0.7rem 0.85rem;
}

.status-card .label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  font-weight: 600;
}

.status-card .value {
  margin-top: 0.18rem;
  font-size: 0.92rem;
  font-weight: 600;
  color: #e2e8f0;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.12rem 0.5rem;
  border-radius: 999px;
  background: rgba(45, 212, 191, 0.12);
  color: #5eead4;
  font-size: 0.78rem;
}

.sidebar-section {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #64748b;
  margin: 1.15rem 0 0.55rem;
}

.disclaimer-card {
  margin-top: 0.75rem;
  padding: 0.9rem;
  border-radius: 12px;
  background: rgba(251, 191, 36, 0.08);
  border: 1px solid rgba(251, 191, 36, 0.18);
  color: #e2e8f0;
  font-size: 0.78rem;
  line-height: 1.45;
}

.example-card {
  height: 100%;
  padding: 0.95rem 1rem;
  border-radius: 14px;
  background: #121a2b;
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.example-card h4 {
  margin: 0 0 0.3rem;
  font-size: 0.95rem;
  color: #f1f5f9;
}

.example-card p {
  margin: 0;
  color: #94a3b8;
  font-size: 0.82rem;
  line-height: 1.4;
}

div[data-testid="stChatMessage"] {
  background: transparent;
  padding: 0.15rem 0;
}

div[data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] {
  background: linear-gradient(160deg, #2dd4bf, #0ea5e9) !important;
  color: #0b1220 !important;
}

.user-bubble, .triage-card, .assessment-card, .sources-card, .refusal-card, .audit-card {
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.user-bubble {
  background: rgba(14, 165, 233, 0.10);
  padding: 0.9rem 1.05rem;
  color: #e2e8f0;
  font-size: 1.02rem;
  line-height: 1.5;
}

.triage-card {
  padding: 1rem 1.1rem 1.05rem;
  margin-bottom: 0.75rem;
}

.triage-card.self { background: rgba(52, 211, 153, 0.08); border-color: rgba(52, 211, 153, 0.28); }
.triage-card.consult { background: rgba(251, 191, 36, 0.08); border-color: rgba(251, 191, 36, 0.28); }
.triage-card.emergency { background: rgba(248, 113, 113, 0.10); border-color: rgba(248, 113, 113, 0.35); }

.triage-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.45rem;
}

.triage-badge {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.triage-card.self .triage-badge { color: #6ee7b7; }
.triage-card.consult .triage-badge { color: #fcd34d; }
.triage-card.emergency .triage-badge { color: #fca5a5; }

.triage-card h3 {
  margin: 0;
  font-size: 1.18rem;
  color: #f8fafc;
}

.triage-card p {
  margin: 0.35rem 0 0;
  color: #cbd5e1;
  line-height: 1.5;
}

.assessment-card, .sources-card, .refusal-card {
  background: #121a2b;
  padding: 1.05rem 1.15rem;
  margin-bottom: 0.75rem;
}

.assessment-card h3, .sources-card h3 {
  margin: 0 0 0.55rem;
  font-size: 0.78rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #64748b;
}

.assessment-body {
  color: #e2e8f0;
  line-height: 1.65;
  font-size: 1.02rem;
  white-space: pre-wrap;
}

.source-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.7rem 0;
  border-top: 1px solid rgba(148, 163, 184, 0.10);
}

.source-row:first-of-type { border-top: none; padding-top: 0.15rem; }

.source-title {
  font-weight: 600;
  color: #f1f5f9;
}

.source-meta {
  color: #94a3b8;
  font-size: 0.82rem;
  margin-top: 0.15rem;
}

.source-score {
  flex-shrink: 0;
  font-size: 0.75rem;
  font-weight: 600;
  color: #5eead4;
  background: rgba(45, 212, 191, 0.10);
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  height: fit-content;
}

.refusal-card {
  background: rgba(248, 113, 113, 0.10);
  border-color: rgba(248, 113, 113, 0.32);
  color: #fecaca;
}

.audit-card {
  background: #121a2b;
  padding: 1.05rem 1.15rem;
  margin-bottom: 0.75rem;
}

.audit-card h3 {
  margin: 0 0 0.55rem;
  font-size: 0.78rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #64748b;
}

.audit-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.45rem;
}

.audit-verdict {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border-radius: 999px;
  padding: 0.18rem 0.55rem;
}

.audit-verdict.pass { color: #6ee7b7; background: rgba(52, 211, 153, 0.12); }
.audit-verdict.partial { color: #fcd34d; background: rgba(251, 191, 36, 0.12); }
.audit-verdict.fail { color: #fca5a5; background: rgba(248, 113, 113, 0.12); }
.audit-verdict.n_a { color: #94a3b8; background: rgba(148, 163, 184, 0.12); }

.audit-summary {
  color: #cbd5e1;
  font-size: 0.92rem;
  line-height: 1.45;
  margin: 0 0 0.55rem;
}

.claim-row {
  display: flex;
  justify-content: space-between;
  gap: 0.85rem;
  padding: 0.6rem 0;
  border-top: 1px solid rgba(148, 163, 184, 0.10);
}

.claim-text {
  color: #e2e8f0;
  font-size: 0.9rem;
  line-height: 1.45;
}

.claim-status {
  flex-shrink: 0;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  height: fit-content;
  padding: 0.18rem 0.5rem;
  border-radius: 999px;
}

.claim-status.supported { color: #6ee7b7; background: rgba(52, 211, 153, 0.12); }
.claim-status.unsupported, .claim-status.fabricated_citation {
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.12);
}

.fine-print {
  color: #64748b !important;
  font-size: 0.75rem !important;
}

[data-testid="stChatInput"] {
  max-width: 1080px;
  margin: 0 auto;
}

[data-testid="stChatInput"] textarea {
  background: #121a2b !important;
  color: #e8eef7 !important;
}

div.stButton > button {
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: #121a2b;
  color: #e2e8f0;
}

div.stButton > button:hover {
  border-color: rgba(45, 212, 191, 0.45);
  color: #5eead4;
}

.stSlider label, .stSlider p {
  color: #94a3b8 !important;
}
</style>
"""


def _esc(value: object) -> str:
    return html.escape(str(value or ""))


def _render_html(body: str) -> None:
    """Render HTML without Streamlit treating indented tags as a code block."""
    st.html(textwrap.dedent(body).strip())


def _format_answer(text: str) -> str:
    escaped = _esc(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped.replace("\n", "<br>")


def _render_user(query: str) -> None:
    _render_html(f'<div class="user-bubble">{_esc(query)}</div>')


def _render_assistant(entry: dict) -> None:
    if entry.get("error"):
        st.error(entry["error"])
        return

    if entry.get("refused"):
        _render_html(
            f"""
            <div class="refusal-card">
              <strong>Request not answered</strong>
              <p>{_esc(entry.get("answer"))}</p>
            </div>
            """
        )
        st.caption(entry.get("disclaimer") or config.DISCLAIMER)
        return

    level = entry.get("triage_level") or "consult_doctor"
    meta = TRIAGE_META.get(level, TRIAGE_META["consult_doctor"])
    _render_html(
        f"""
        <div class="triage-card {meta["tone"]}">
          <div class="triage-top">
            <span class="triage-badge">{meta["icon"]} {meta["badge"]}</span>
          </div>
          <h3>{_esc(entry.get("triage_label"))}</h3>
          <p>{_esc(entry.get("triage_guidance"))}</p>
        </div>
        """
    )

    _render_html(
        f"""
        <div class="assessment-card">
          <h3>Grounded assessment</h3>
          <div class="assessment-body">{_format_answer(entry.get("answer") or "")}</div>
        </div>
        """
    )

    citations = entry.get("citations") or []
    if citations:
        rows = []
        for item in citations:
            url = item.get("url") or ""
            title = _esc(item.get("title") or "Source")
            title_html = (
                f'<a href="{_esc(url)}" target="_blank" rel="noreferrer">{title}</a>'
                if url
                else title
            )
            score = item.get("relevance_score")
            score_html = (
                f'<span class="source-score">{score:.0%}</span>'
                if isinstance(score, (int, float))
                else ""
            )
            rows.append(
                "<div class='source-row'>"
                "<div>"
                f"<div class='source-title'>{title_html}</div>"
                f"<div class='source-meta'>{_esc(item.get('source'))}</div>"
                "</div>"
                f"{score_html}"
                "</div>"
            )
        _render_html(
            "<div class='sources-card'>"
            "<h3>Retrieved sources</h3>"
            + "".join(rows)
            + "</div>"
        )

    audit = entry.get("faithfulness")
    if audit:
        verdict = audit.get("verdict") or "n_a"
        coverage = audit.get("coverage")
        coverage_label = f"{coverage:.0%}" if isinstance(coverage, (int, float)) else "—"
        claim_rows = []
        for claim in audit.get("claims") or []:
            status = claim.get("status")
            if status == "not_a_claim":
                continue
            status_label = {
                "supported": "Supported",
                "unsupported": "No citation",
                "fabricated_citation": "Not retrieved",
            }.get(status, status)
            claim_rows.append(
                "<div class='claim-row'>"
                f"<div class='claim-text'>{_esc(claim.get('text'))}</div>"
                f"<span class='claim-status { _esc(status) }'>{_esc(status_label)}</span>"
                "</div>"
            )
        _render_html(
            "<div class='audit-card'>"
            "<h3>Citation faithfulness audit</h3>"
            "<div class='audit-head'>"
            f"<span class='audit-verdict { _esc(verdict) }'>{_esc(verdict.replace('_', ' '))}</span>"
            f"<span class='source-score'>{_esc(coverage_label)} coverage</span>"
            "</div>"
            f"<p class='audit-summary'>{_esc(audit.get('summary'))}</p>"
            + "".join(claim_rows)
            + "</div>"
        )

    st.caption(entry.get("disclaimer") or config.DISCLAIMER)


def _entry_from_result(query: str, result) -> dict:
    return {
        "query": query,
        "refused": result.refused,
        "answer": result.answer,
        "triage_level": None if result.triage is None else result.triage.level,
        "triage_label": None if result.triage is None else result.triage.label,
        "triage_guidance": None if result.triage is None else result.triage.guidance,
        "citations": result.citations,
        "faithfulness": None if result.faithfulness is None else result.faithfulness.to_dict(),
        "disclaimer": result.disclaimer,
        "error": None,
    }


st.markdown(APP_CSS, unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

with st.sidebar:
    st.markdown(
        """
        <div class="brand">
          <div class="brand-mark">🩺</div>
          <div>
            <h1>Diagnosis Assistant</h1>
            <p>LLM + RAG clinical demo</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section">Session</div>', unsafe_allow_html=True)
    provider = config.resolve_llm_provider()
    provider_note = (
        '<span class="pill">works without an API key</span>' if provider == "mock" else ""
    )
    st.markdown(
        f"""
        <div class="status-grid">
          <div class="status-card">
            <div class="label">Embedding model</div>
            <div class="value">{_esc(config.EMBEDDING_MODE)}</div>
          </div>
          <div class="status-card">
            <div class="label">Language model</div>
            <div class="value">{_esc(provider)} {provider_note}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section">Retrieval</div>', unsafe_allow_html=True)
    top_k = st.slider("Passages to retrieve", min_value=1, max_value=8, value=config.TOP_K)

    if st.button("Start new conversation", use_container_width=True):
        st.session_state.history = []
        st.session_state.pending_query = None
        st.rerun()

    st.markdown(
        f'<div class="disclaimer-card">{_esc(config.DISCLAIMER)}</div>',
        unsafe_allow_html=True,
    )

pending_query = st.session_state.pending_query
show_empty_state = not st.session_state.history and not pending_query

if show_empty_state:
    st.markdown(
        """
        <div class="hero">
          <div class="hero-kicker">Grounded · Cited · Triage-aware</div>
          <h2>Describe symptoms. Get a cited assessment.</h2>
          <p>
            The assistant retrieves trusted reference passages, assigns a triage
            level, and answers only from those sources. It does not replace a clinician.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    for col, example in zip(cols, EXAMPLE_QUERIES):
        with col:
            st.markdown(
                f"""
                <div class="example-card">
                  <h4>{_esc(example['title'])}</h4>
                  <p>{_esc(example['hint'])}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Try this", key=f"ex_{example['title']}", use_container_width=True):
                st.session_state.pending_query = example["text"]
                st.rerun()

for entry in st.session_state.history:
    with st.chat_message("user"):
        _render_user(entry["query"])
    with st.chat_message("assistant"):
        if "rendered" in entry and "triage_level" not in entry:
            st.markdown(entry["rendered"])
        else:
            _render_assistant(entry)

typed_query = st.chat_input("Describe your symptoms in plain language…")
query = pending_query or typed_query
if pending_query:
    st.session_state.pending_query = None

if query:
    with st.spinner("Checking safety, retrieving references, and drafting a grounded answer…"):
        try:
            result = run_pipeline(query, top_k=top_k)
            entry = _entry_from_result(query, result)
        except Exception as exc:
            entry = {
                "query": query,
                "error": f"Something went wrong: {exc}",
                "refused": False,
                "answer": "",
                "citations": [],
                "disclaimer": config.DISCLAIMER,
            }
    st.session_state.history.append(entry)
    st.rerun()
