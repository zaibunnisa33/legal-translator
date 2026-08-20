import os
import tempfile
import streamlit as st
from openai import OpenAI

from translator import extract, rebuild
from translator.translate import translate_document

st.set_page_config(page_title="Legal Document Translator", layout="wide")
st.title("Legal Document Translator")
st.caption(
    "Upload a PDF, Word (.docx), or image (JPEG/PNG) legal document. "
    "Each section is translated, back-translated, checked against the "
    "original, and corrected — then rebuilt as a Word document."
)

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API key", type="password", value=os.environ.get("OPENAI_API_KEY", ""))
    model = st.selectbox("Model", ["gpt-4o", "gpt-4o-mini", "gpt-4.1"], index=0)
    source_lang = st.text_input("Source language", value="English")
    target_lang = st.text_input("Target language", value="Urdu")
    glossary = st.text_area(
        "Optional glossary (one mapping per line, e.g. 'Special Guardianship Order = اسپیشل گارڈین شپ آرڈر')",
        height=120,
    )
    chunk_size = st.slider("Chunk size (characters)", 500, 4000, 1800, step=100)
    st.markdown("---")
    st.caption("Your API key is only used for this session and is not stored.")

uploaded = st.file_uploader("Upload document", type=["docx", "pdf", "jpg", "jpeg", "png"])

if uploaded and st.button("Translate document", type="primary"):
    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
        st.stop()

    client = OpenAI(api_key=api_key)

    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = os.path.join(tmpdir, uploaded.name)
        with open(in_path, "wb") as f:
            f.write(uploaded.getbuffer())

        st.write("Extracting text…")
        ext = os.path.splitext(uploaded.name)[1].lower()
        if ext == ".docx":
            blocks = extract.extract_docx(in_path)
        elif ext == ".pdf":
            blocks = extract.extract_pdf(client, in_path, model=model)
        elif ext in (".jpg", ".jpeg", ".png"):
            blocks = extract.extract_image(client, in_path, model=model)
        else:
            st.error("Unsupported file type.")
            st.stop()

        if not blocks:
            st.error("No text could be extracted from this file.")
            st.stop()

        st.success(f"Extracted {len(blocks)} text blocks.")

        block_chunks = extract.chunk_blocks(blocks, max_chars=chunk_size)
        st.write(f"Translating in {len(block_chunks)} chunk(s) — each chunk is translated, "
                 f"back-translated, checked, and corrected…")

        progress = st.progress(0.0)
        status = st.empty()

        def on_progress(i, total):
            progress.progress(i / total)
            status.write(f"Chunk {i}/{total} complete")

        results = translate_document(
            client, block_chunks, source_lang, target_lang,
            model=model, glossary=glossary, progress_callback=on_progress,
        )

        st.write("Rebuilding Word document…")
        out_name = rebuild.output_filename(uploaded.name, target_lang)
        out_path = os.path.join(tmpdir, out_name)
        rebuild.build_docx(results, target_lang, out_path)

        with open(out_path, "rb") as f:
            data = f.read()

        st.success("Done.")
        st.download_button(
            "Download translated document",
            data=data,
            file_name=out_name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        with st.expander("Review comparison notes per chunk"):
            for i, r in enumerate(results):
                st.markdown(f"**Chunk {i+1}**")
                st.text(r.comparison_notes)
