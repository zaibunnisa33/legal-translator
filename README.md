# Legal Document Translator

A deployable web app that translates legal documents (PDF, Word, or JPEG/PNG)
using ChatGPT, following a strict translate → back-translate → compare →
correct workflow per section, then rebuilds the result as a Word document in
Times New Roman (with automatic right-to-left formatting for RTL languages
like Urdu, Arabic, Farsi, Hebrew).

## How it works

1. **Extract**: pulls text block-by-block (headings, paragraphs, table cells)
   from the uploaded file. Scanned PDFs and images are read with GPT-4o
   Vision OCR (transcription only, no translation at this step).
2. **Chunk**: groups blocks into ~1800-character chunks without splitting a
   paragraph across chunks (adjustable in the sidebar).
3. **Translate each chunk**, as one continuous ChatGPT conversation:
   - Translate the chunk (formal legal tone, terms preserved/bracketed,
     names transliterated, numbering/structure preserved).
   - Back-translate the result into the source language.
   - Compare the back-translation against the original and list any
     omissions, additions, changed meaning, wrong terms, wrong names/dates.
   - Produce the corrected final translation.
4. **Rebuild**: writes a new .docx with the translated text in the same
   paragraph order/structure as the original, forced to Times New Roman,
   right-aligned and RTL-tagged automatically for RTL target languages.
5. **Output filename**: `<original name>_<target language>.docx`
   (e.g. `Settlement Agreement_Urdu.docx`).

The exact rule set sent to ChatGPT is in `translator/prompts.py` — edit it
directly to change tone, add glossary term-mappings, or adjust rules for a
specific language pair. The sidebar in the app also has a free-text glossary
box for one-off term mappings without touching code.

## Running locally

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...      # or paste it into the app's sidebar
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

## Deploying so others can use it

**Easiest — Streamlit Community Cloud (free):**
1. Push this folder to a GitHub repo.
2. Go to https://share.streamlit.io, connect the repo, set `app.py` as the
   entry point.
3. Add `OPENAI_API_KEY` under the app's "Secrets" settings (or leave it
   blank and let each user paste their own key in the sidebar).

**Anywhere else — Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```
Build and run with `docker build -t legal-translator . && docker run -p 8501:8501 -e OPENAI_API_KEY=sk-... legal-translator`,
then deploy that container to Render, Fly.io, Azure Container Apps, AWS App
Runner, etc.

## Notes / limitations

- Requires an OpenAI **API key** (usage is billed per token, separate from a
  ChatGPT Plus subscription — Plus doesn't give API access).
- Current formatting preservation is paragraph-level (font, bold, headings,
  bullets, right-to-left). Complex layouts — multi-column pages, precise
  table grids, images anchored mid-paragraph — are flattened to paragraphs;
  extend `translator/rebuild.py` if you need pixel-perfect layout cloning.
- PowerPoint (.pptx) output isn't wired up yet (Word was the stated
  priority). The same block/translate/rebuild pattern extends to `.pptx`
  using `python-pptx` if you want it added.
- For very long documents, expect the per-chunk 4-call workflow (translate,
  back-translate, compare, correct) to take a while and to cost roughly 4x
  a plain one-shot translation — that's the trade-off for the accuracy
  checking you asked for.
