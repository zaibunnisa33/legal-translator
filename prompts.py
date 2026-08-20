"""
Prompt templates for the legal-translation workflow.

Workflow per chunk (all turns sent in ONE conversation thread so the model
keeps context, exactly like doing it by hand in ChatGPT):
    1. system + translate_prompt   -> forward translation
    2. back_translate_prompt       -> back-translation into source language
    3. compare_prompt              -> line-by-line comparison / error list
    4. updated_translation_prompt  -> corrected final translation

Edit the RULES text below to tune terminology, tone, or add more example
name/term mappings for your language pairs.
"""

RTL_LANGUAGES = {
    "urdu", "arabic", "farsi", "persian", "hebrew", "pashto", "dari", "sindhi",
    "kurdish (sorani)", "uyghur",
}


def is_rtl(language: str) -> bool:
    return language.strip().lower() in RTL_LANGUAGES


def build_system_prompt(source_lang: str, target_lang: str, glossary: str = "") -> str:
    """The 'Act as an expert legal translator...' framing + the detailed rule set,
    generalised so it works for any source/target language pair."""

    glossary_block = f"\nGlossary / fixed term-mappings to use consistently:\n{glossary}\n" if glossary.strip() else ""

    return f"""Act as an expert legal translator fluent in both {source_lang} legal language and {target_lang} legal language.

Translate the {source_lang} legal text I provide into {target_lang}. Follow these strict rules:

1. Accuracy: Provide a faithful, word-for-word-where-possible legal translation. Do not omit, add, or alter any facts, clauses, terms, names, dates, case numbers, section numbers, paragraph numbers, references or abbreviations.
2. Tone: Maintain a highly formal, authoritative, professional legal tone using standard {target_lang} legal terminology.
3. Flow: The translation must read naturally and be grammatically correct in formal {target_lang} legal style, while strictly preserving the exact legal meaning of the original {source_lang} text.
4. Do not paraphrase where doing so could alter the legal meaning.
5. Preserve the exact meaning, scope, sequence and structure of the original. Do not "improve", interpret, correct, or explain the source unless specifically asked to.
6. Names of people, places, and organisations must be transliterated into {target_lang} script (not translated), unless {target_lang} conventionally uses the Latin alphabet.
7. Where a term is a specific technical/legal term of the source jurisdiction with no exact equivalent, translate it and then retain the original {source_lang} term in brackets, e.g. translated-term (Original Term).
8. Preserve original headings, numbering, bullet points, tables and layout as closely as possible.
9. For direct quotations, translate exactly what was said, without inserting explanatory words not present in the original.
10. If the source text itself appears grammatically incorrect or contains an apparent typo, do not silently fix its meaning — translate what is actually written and flag the issue separately if necessary.
11. Legal terms must be translated consistently throughout the entire document.
12. Accuracy takes priority over making the {target_lang} text shorter or simpler. The translation must correspond as closely as possible to the original, without omissions or additions.
{glossary_block}
I will send you the document in chunks. For each chunk, simply reply with the {target_lang} translation and nothing else (no preamble, no notes) unless I explicitly ask you for a back-translation, a comparison, or an updated version."""


DELIMITER = "\n§§§\n"


def translate_prompt(chunk_text: str) -> str:
    return (
        f"Translate the following text. It is made up of several segments separated by the "
        f"exact marker '{DELIMITER.strip()}' on its own line. Your reply MUST contain the same "
        f"number of segments, in the same order, separated by that exact same marker on its own "
        f"line, so segments can be matched back to the original layout. Do not merge, split, or "
        f"reorder segments. Do not add any extra commentary before or after.\n\n{chunk_text}"
    )


def back_translate_prompt(source_lang: str) -> str:
    return (
        f"Now translate the translation you just gave me back into {source_lang}, "
        f"as literally and accurately as possible, so it can be checked against the original. "
        f"Reply with only the back-translation."
    )


def compare_prompt() -> str:
    return (
        "Now compare your back-translation against the original source text I gave you, "
        "line-by-line, and identify:\n"
        "1. omissions\n"
        "2. additions\n"
        "3. changed meaning\n"
        "4. incorrect terminology\n"
        "5. incorrect names/dates/numbers\n"
        "6. mistranslated legal or technical terms\n\n"
        "List the issues found (or state 'No issues found' if none)."
    )


def updated_translation_prompt(target_lang: str) -> str:
    return (
        f"Now give me the corrected {target_lang} translation, incorporating only the necessary "
        f"corrections identified in your comparison above. Reply with only the corrected {target_lang} "
        f"translation, nothing else."
    )
