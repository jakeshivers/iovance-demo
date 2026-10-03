"""Streamlit UI over the existing rag functions."""
from pathlib import Path

import streamlit as st

from rag.generate import REFUSAL, answer, make_llm
from rag.retrieve import CFG, cite

MODES = ["vector", "hybrid", "hybrid_rerank"]

st.sidebar.header("Document library")
for pdf in sorted(Path("static").glob("*.pdf")):
    st.sidebar.markdown(f"[{pdf.stem}](app/static/{pdf.name})")

st.title("Regulatory RAG Demo")
mode = st.selectbox("Retrieval mode", MODES, index=MODES.index(CFG["retrieval"]))
q = st.text_input("Question")

if q:
    with st.spinner("Searching..."):
        text, hits = answer(q, make_llm(), mode)
    if REFUSAL in text:
        st.error("Refused: insufficient context in the indexed guidance to answer this.")
    else:
        st.markdown(text)
    score_label = "rerank score" if mode == "hybrid_rerank" else f"{mode} score"
    for h in hits:
        with st.expander(f"{cite(h)} · {score_label} {h['score']:.3f}"):
            st.write(f"**Doc:** {h['doc']}  **Section:** {h['section']}  **Page:** {h['page']}")
            st.text(h["text"])
