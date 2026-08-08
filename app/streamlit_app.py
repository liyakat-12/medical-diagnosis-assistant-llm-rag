"""
Streamlit chat UI for the Medical Diagnosis Assistant.

Run with:
    streamlit run app/streamlit_app.py

Talks directly to the pipeline in-process (no need to run the FastAPI
server separately) so it also works as a quick local demo.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from src import config
from src.pipeline.rag_pipeline import run_pipeline

st.set_page_config(page_title="Medical Diagnosis Assistant", page_icon="🩺", layout="centered")

TRIAGE_COLORS = {
    "self_care": "🟢",
    "consult_doctor": "🟡",
    "emergency": "🔴",
}

st.title("🩺 Medical Diagnosis Assistant")
st.caption("LLM + RAG demo — grounded, cited, triage-aware. **Not a substitute for professional care.**")

with st.sidebar:
    st.header("Settings")
    st.write(f"**Embedding mode:** `{config.EMBEDDING_MODE}`")
    st.write(f"**LLM provider:** `{config.LLM_PROVIDER}`")
    top_k = st.slider("Number of retrieved passages (top-k)", min_value=1, max_value=8, value=config.TOP_K)
    st.divider()
    st.warning(config.DISCLAIMER)

if "history" not in st.session_state:
    st.session_state.history = []

for entry in st.session_state.history:
    with st.chat_message("user"):
        st.write(entry["query"])
    with st.chat_message("assistant"):
        st.markdown(entry["rendered"])

query = st.chat_input("Describe your symptoms in plain language...")

if query:
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving relevant medical references and generating a grounded answer..."):
            try:
                result = run_pipeline(query, top_k=top_k)
            except Exception as exc:  # surface config/LLM errors clearly in the UI
                st.error(f"Something went wrong: {exc}")
                st.stop()

        rendered_parts = []

        if result.refused:
            st.error(result.answer)
            rendered_parts.append(f"**Refused:** {result.answer}")
        else:
            emoji = TRIAGE_COLORS.get(result.triage.level, "🟡")
            st.markdown(f"### {emoji} Triage: {result.triage.label}")
            st.write(result.triage.guidance)
            rendered_parts.append(f"### {emoji} Triage: {result.triage.label}\n\n{result.triage.guidance}")

            st.markdown("### Assessment")
            st.write(result.answer)
            rendered_parts.append(f"### Assessment\n\n{result.answer}")

            if result.citations:
                st.markdown("### Sources retrieved")
                for c in result.citations:
                    label = f"- **{c['title']}** — {c['source']} (relevance {c['relevance_score']:.2f})"
                    if c["url"]:
                        label += f" — [link]({c['url']})"
                    st.markdown(label)
                citation_md = "\n".join(
                    f"- **{c['title']}** — {c['source']}" + (f" — [link]({c['url']})" if c["url"] else "")
                    for c in result.citations
                )
                rendered_parts.append(f"### Sources retrieved\n\n{citation_md}")

        st.caption(result.disclaimer)
        rendered_parts.append(f"*{result.disclaimer}*")

        st.session_state.history.append({"query": query, "rendered": "\n\n".join(rendered_parts)})
