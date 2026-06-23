from fastapi import APIRouter
from pydantic import BaseModel
from services.llm_service import generate_response
import re

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


# ── Inline styles ─────────────────────────────────────────────
def apply_inline_styles(text: str) -> str:
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r'<strong class="notes-bold">\1</strong>', text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r'<code class="notes-code">\1</code>', text)
    return text


# ── Markdown → HTML ───────────────────────────────────────────
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


# ── Route ─────────────────────────────────────────────────────
@router.post("/chat")
def chat(data: ChatRequest):

    prompt = f"""
You are an AI tutor.

Explain clearly:
{data.message}

Use:
- Simple explanation
- Step-by-step logic
- Example if needed
"""

    response = generate_response(prompt)

    # Convert markdown → HTML before sending to frontend
    reply_html = markdown_to_html(response) if response else "No response. Try again."

    return {
        "reply": reply_html
    }