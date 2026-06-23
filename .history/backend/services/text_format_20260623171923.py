"""
services/text_format.py

Extracted from api/chat.py (Phase 8) so the new conversation-aware chat
endpoints don't duplicate this logic. Behaviour is unchanged except for
the prompt style — see SIMPLE_TUTOR_FORMAT below.
"""

import html
import re


# ── Simple, plain-prose answer style ────────────────────────────────────────
# Earlier this used a "MARKDOWN_TUTOR_FORMAT" that forced every answer into
# a report template: H1/H2/H3 headings, bullet lists, numbered lists, a
# comparison table, a blockquote callout, and "---" dividers. That's the
# rigid, document-style look. Switched to plain conversational prose —
# short paragraphs, no forced structure. No translation/transliteration
# template either — instead, when a verse/line from the attached PDF or
# photo is quoted, it's bolded exactly as-is so it visually stands out from
# the surrounding plain-text explanation. Bold is reserved for that case only.
SIMPLE_TUTOR_FORMAT = """
Answer in plain, simple text — like a knowledgeable person explaining something
clearly in conversation, not like a written report.

- Write in short paragraphs. Do not use headings (no #, ##, ###) unless the
  question is specifically about a Sanskrit/Hindi/Marathi verse (see below).
- Do not use Markdown tables.
- Do not use blockquote callouts (no "> [!NOTE]" or similar).
- Do not use horizontal rule dividers ("---").
- Only use a bullet or numbered list when the content is genuinely a list of
  steps or items the student needs to follow in order. Otherwise just write
  sentences.
- Do not bold key terms, names, or random phrases for emphasis. The only
  thing that should ever be bold is an original verse/line quoted exactly
  from the attached PDF or photo (see below).
- Keep the tone warm and direct, the way a tutor would actually talk.

Rules for retrieved study material:
- Treat retrieved chunks as private reference notes, not as text to paste.
- Never output retrieved chunks verbatim — except for the original
  verse/line itself, per the rule below. Everything else (surrounding
  explanation, OCR notes, paragraph text) must be paraphrased in your own
  words.
- Summarize and explain the content in your own words.
- If context is incomplete, say plainly what is missing, then explain what
  can still be answered.

When the original verse, shloka, or line (in Sanskrit/Hindi/Marathi or any
other language) is present in the attached PDF or photo, quote it exactly as
it appears in the source script and wrap it in **bold** so it stands out
clearly from your explanation, like this: **मूळ श्लोक इथे येईल**. Do not
translate or transliterate it — just bold the original text, then explain
its meaning in plain language right after, in your own words. Do not bold
anything else in the answer except this original quoted text.
""".strip()

# Backwards-compatible alias in case other modules still import the old name.
MARKDOWN_TUTOR_FORMAT = SIMPLE_TUTOR_FORMAT


def apply_inline_styles(text: str) -> str:
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r'<strong class="notes-bold">\1</strong>', text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r'<code class="notes-code">\1</code>', text)
    return text


def markdown_to_html(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines = text.split("\n")
    html_lines = []
    in_ul = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("### "):
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<h3 class="notes-h3">{apply_inline_styles(stripped[4:])}</h3>')

        elif stripped.startswith("## "):
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<h2 class="notes-h2">{apply_inline_styles(stripped[3:])}</h2>')

        elif stripped.startswith("# "):
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<h1 class="notes-h1">{apply_inline_styles(stripped[2:])}</h1>')

        elif stripped in ("---", "***", "___"):
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append('<hr class="notes-hr" />')

        elif re.match(r"^[\*\-\+]\s+", stripped):
            content = apply_inline_styles(re.sub(r"^[\*\-\+]\s+", "", stripped))
            if not in_ul:
                html_lines.append('<ul class="notes-ul">'); in_ul = True
            html_lines.append(f'  <li class="notes-li">{content}</li>')

        elif re.match(r"^\d+\.\s+", stripped):
            content = apply_inline_styles(re.sub(r"^\d+\.\s+", "", stripped))
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<p class="notes-numbered">• {content}</p>')

        elif stripped == "":
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append("")

        else:
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<p class="notes-p">{apply_inline_styles(stripped)}</p>')

    if in_ul:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def normalize_legacy_answer(text: str) -> str:
    """
    Convert old notes-* HTML answers back into Markdown-ish text.

    Older chat replies were saved after markdown_to_html(), so once the
    frontend switched to react-markdown those tags appeared as visible text.
    This keeps old messages readable and prevents HTML from leaking back into
    future prompts.
    """
    if not text:
        return ""

    normalized = html.unescape(text)

    replacements = [
        (r"<h1[^>]*>(.*?)</h1>", r"# \1\n\n"),
        (r"<h2[^>]*>(.*?)</h2>", r"## \1\n\n"),
        (r"<h3[^>]*>(.*?)</h3>", r"### \1\n\n"),
        (r"<hr[^>]*\/?>", r"\n---\n"),
        (r"<li[^>]*>(.*?)</li>", r"- \1\n"),
        (r"<p[^>]*class=[\"']notes-numbered[\"'][^>]*>\s*â€¢\s*(.*?)</p>", r"1. \1\n\n"),
        (r"<p[^>]*class=[\"']notes-numbered[\"'][^>]*>\s*•\s*(.*?)</p>", r"1. \1\n\n"),
        (r"<p[^>]*>(.*?)</p>", r"\1\n\n"),
        (r"<strong[^>]*>(.*?)</strong>", r"**\1**"),
        (r"<em[^>]*>(.*?)</em>", r"*\1*"),
        (r"<code[^>]*>(.*?)</code>", r"`\1`"),
    ]
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE | re.DOTALL)

    normalized = re.sub(r"</?(ul|ol)[^>]*>", "\n", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"<br\s*/?>", "\n", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"<[^>]+>", "", normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def build_rag_prompt(question: str, context_chunks: list[str]) -> str:
    context_text = "\n\n--- SOURCE NOTE ---\n\n".join(
        f"Reference note {index}:\n{chunk}"
        for index, chunk in enumerate(context_chunks, start=1)
    )
    return f"""You are an expert AI tutor helping a student understand their uploaded study material.

{SIMPLE_TUTOR_FORMAT}

The following retrieved notes are for your grounding only. They may be fragmentary OCR/PDF chunks.
Use them to identify facts, concepts, and structure, but do not copy their wording into the answer.

{context_text}

---

Student question:
{question}

Answer directly and plainly, in your own words, the way a tutor would explain it out loud.
If the source notes contain an original verse/line, quote it exactly in **bold**, then explain
it in plain language — don't bold anything else.
"""


def build_plain_prompt(question: str) -> str:
    return f"""You are an expert AI tutor.

{SIMPLE_TUTOR_FORMAT}

Student question:
{question}

Answer directly and plainly, in your own words, the way a tutor would explain it out loud.
"""