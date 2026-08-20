"""
Runs the translate -> back-translate -> compare -> corrected-translation
workflow for each chunk of blocks, as one continuous conversation thread per
chunk, then maps the final translated segments back onto the original blocks.
"""
from dataclasses import dataclass, field

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from . import prompts


@dataclass
class ChunkResult:
    blocks: list          # original blocks in this chunk
    translated_texts: list  # translated text per block, same order/length
    first_translation: str
    back_translation: str
    comparison_notes: str
    thread: list = field(default_factory=list)


def _split_segments(text: str, expected_count: int) -> list[str]:
    parts = [p.strip() for p in text.split(prompts.DELIMITER.strip())]
    if len(parts) != expected_count:
        parts = [p.strip() for p in text.replace(prompts.DELIMITER, "\n§§§\n").split("§§§")]
    if len(parts) != expected_count:
        # Fallback: model didn't preserve the marker exactly. Pad/truncate so the
        # document still builds; comparison step still ran on the full text.
        if len(parts) < expected_count:
            parts += [""] * (expected_count - len(parts))
        else:
            parts = parts[:expected_count]
    return parts


def translate_chunk(
    client: OpenAI,
    blocks: list[dict],
    source_lang: str,
    target_lang: str,
    model: str = "gpt-4o",
    glossary: str = "",
    temperature: float = 0.2,
) -> ChunkResult:
    chunk_text = prompts.DELIMITER.join(b["text"] for b in blocks)

    system = prompts.build_system_prompt(source_lang, target_lang, glossary)
    thread = [{"role": "system", "content": system}]

    def ask(user_msg: str) -> str:
        thread.append({"role": "user", "content": user_msg})
        resp = client.chat.completions.create(
            model=model,
            messages=thread,
            temperature=temperature,
        )
        reply = resp.choices[0].message.content.strip()
        thread.append({"role": "assistant", "content": reply})
        return reply

    first_translation = ask(prompts.translate_prompt(chunk_text))
    back_translation = ask(prompts.back_translate_prompt(source_lang))
    comparison_notes = ask(prompts.compare_prompt())
    final_translation = ask(prompts.updated_translation_prompt(target_lang))

    translated_texts = _split_segments(final_translation, len(blocks))

    return ChunkResult(
        blocks=blocks,
        translated_texts=translated_texts,
        first_translation=first_translation,
        back_translation=back_translation,
        comparison_notes=comparison_notes,
        thread=thread,
    )


def translate_document(
    client: OpenAI,
    block_chunks: list[list[dict]],
    source_lang: str,
    target_lang: str,
    model: str = "gpt-4o",
    glossary: str = "",
    progress_callback=None,
) -> list[ChunkResult]:
    """Translate a list of block-chunks in order. Calls
    progress_callback(i, total) after each chunk if provided."""
    results = []
    total = len(block_chunks)
    for i, blocks in enumerate(block_chunks):
        results.append(
            translate_chunk(client, blocks, source_lang, target_lang, model, glossary)
        )
        if progress_callback:
            progress_callback(i + 1, total)
    return results
