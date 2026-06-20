"""
PDF report generation for the meeting summarizer.

Produces a formatted PDF containing the summary, action items, and full
transcript - mirroring the Markdown report from the CLI pipeline, but as
a downloadable PDF from the web interface.

Multi-language support: Whisper auto-detects the spoken language and
transcribes in that same language (it does not translate). Rendering that
text correctly in a PDF requires a font that actually contains the needed
glyphs - no single font covers every writing system well, so this module
picks an appropriate bundled font based on the detected language:

  - Latin / Cyrillic / Greek scripts (most European languages) -> Noto Sans
  - Arabic script                                               -> Noto Sans Arabic
  - Chinese / Japanese / Korean                                 -> Noto Sans SC

Arabic additionally needs reshaping + bidi reordering (arabic_reshaper +
python-bidi) since ReportLab does not do this automatically - without it,
Arabic letters render disconnected and in the wrong visual order.
"""

import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display


FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "fonts")

# Language codes (as returned by Whisper) grouped by which bundled font
# can actually render their script.
ARABIC_LANGS = {"ar", "fa", "ur"}
CJK_LANGS = {"zh", "ja", "ko"}
# Everything else (en, nl, fr, de, es, it, pt, ru, pl, sv, etc.) uses the
# default Noto Sans, which covers Latin, Cyrillic, and Greek scripts.

_FONTS_REGISTERED = False


def _ensure_fonts_registered():
    """Register the bundled fonts with ReportLab, once per process."""
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    pdfmetrics.registerFont(TTFont("NotoSans", os.path.join(FONTS_DIR, "NotoSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("NotoSansArabic", os.path.join(FONTS_DIR, "NotoSansArabic-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("NotoSansSC", os.path.join(FONTS_DIR, "NotoSansSC-Regular.ttf")))
    _FONTS_REGISTERED = True


def _font_for_language(language_code: str) -> str:
    """Pick the bundled font name that can render the given language's script."""
    if language_code in ARABIC_LANGS:
        return "NotoSansArabic"
    if language_code in CJK_LANGS:
        return "NotoSansSC"
    return "NotoSans"


def _prepare_text(text: str, language_code: str) -> str:
    """
    Reshape + bidi-reorder Arabic-script text so it renders with connected
    letters in the correct right-to-left visual order. No-op for other
    scripts.
    """
    if language_code in ARABIC_LANGS:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    return text


def _escape(text: str) -> str:
    """Escape characters that are meaningful in ReportLab's XML-ish markup."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_pdf_report(
    output_path: str,
    source_name: str,
    summary: str,
    action_items: list[str],
    transcript: str,
    language_code: str = "en",
    language_name: str = "English",
) -> str:
    """
    Build a PDF report with summary, action items, and full transcript.

    Args:
        output_path: where to write the PDF file.
        source_name: name of the original recording (shown as the title).
        summary: the generated summary text.
        action_items: list of detected action item sentences.
        transcript: the full transcript text.
        language_code: Whisper's detected language code (e.g. "en", "ar").
        language_name: human-readable language name (e.g. "English").

    Returns:
        The output_path, for convenience.
    """
    _ensure_fonts_registered()
    font = _font_for_language(language_code)
    is_rtl = language_code in ARABIC_LANGS
    alignment = 2 if is_rtl else 0  # 2 = right, 0 = left (ReportLab constants)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    accent = colors.HexColor("#3d6e5a")
    muted = colors.HexColor("#666666")

    title_style = ParagraphStyle(
        "Title", fontName=font, fontSize=20, leading=26, spaceAfter=4,
        textColor=colors.HexColor("#1a1d21"), alignment=alignment,
    )
    meta_style = ParagraphStyle(
        "Meta", fontName=font, fontSize=9, leading=13, textColor=muted,
        spaceAfter=18, alignment=alignment,
    )
    heading_style = ParagraphStyle(
        "Heading", fontName=font, fontSize=12, leading=16, spaceBefore=16,
        spaceAfter=8, textColor=accent, alignment=alignment,
    )
    body_style = ParagraphStyle(
        "Body", fontName=font, fontSize=10.5, leading=16,
        textColor=colors.HexColor("#1a1d21"), alignment=alignment,
    )
    item_style = ParagraphStyle(
        "Item", fontName=font, fontSize=10.5, leading=15,
        textColor=colors.HexColor("#1a1d21"), alignment=alignment,
    )

    story = []
    story.append(Paragraph(_escape(source_name), title_style))
    story.append(Paragraph(
        f"Meeting Summarizer report &middot; detected language: {_escape(language_name)}",
        meta_style,
    ))
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#dddddd")))

    story.append(Paragraph("Summary", heading_style))
    story.append(Paragraph(_escape(_prepare_text(summary, language_code)), body_style))

    story.append(Paragraph("Action Items", heading_style))
    if action_items:
        if is_rtl:
            # ListFlowable's bullets are always left-anchored regardless of
            # paragraph alignment, which looks wrong for RTL text. Use a
            # manual trailing bullet character instead, so it sits on the
            # correct (right) side together with the text.
            for item in action_items:
                text = _escape(_prepare_text(item, language_code))
                story.append(Paragraph(f"{text} &#8226;", item_style))
                story.append(Spacer(1, 4))
        else:
            list_items = [
                ListItem(Paragraph(_escape(_prepare_text(item, language_code)), item_style), bulletColor=accent)
                for item in action_items
            ]
            story.append(ListFlowable(list_items, bulletType="bullet", leftIndent=14, bulletFontSize=8))
    else:
        story.append(Paragraph("No action items detected.", body_style))

    story.append(Paragraph("Full Transcript", heading_style))
    # Split into paragraphs on existing line breaks so very long transcripts
    # still flow and paginate correctly instead of becoming one giant block.
    transcript_text = _prepare_text(transcript, language_code)
    for chunk in transcript_text.split("\n"):
        if chunk.strip():
            story.append(Paragraph(_escape(chunk), body_style))
            story.append(Spacer(1, 6))

    doc.build(story)
    return output_path
