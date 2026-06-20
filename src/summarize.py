"""
Stage 2: Summarization and action item extraction from a transcript.

Runs fully locally - no external API calls. Uses extractive summarization
(LSA algorithm via sumy) to pick the most important sentences, and simple
keyword/pattern matching to find action items.

Usage:
    python src/summarize.py output/your_transcript.txt
"""

import sys
import os
import re

import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer


# Phrases that commonly signal an action item / follow-up task.
# Matched case-insensitively against each sentence.
# Kept deliberately specific (not generic words like "should" or "let's")
# to avoid flagging every other sentence in normal conversation.
ACTION_PATTERNS = [
    r"\bneed(s)? to\b",
    r"\bhave to\b",
    r"\bhas to\b",
    r"\bmust\b",
    r"\bfollow[\s-]?up with\b",
    r"\bmake sure\b",
    r"\baction item\b",
    r"\bto-do\b",
    r"\btodo\b",
    r"\bassign(ed)? to\b",
    r"\bby (monday|tuesday|wednesday|thursday|friday|saturday|sunday|next week|tomorrow|end of)\b",
    r"\bdeadline\b",
    r"\bwill send\b",
    r"\bwill schedule\b",
    r"\bwill follow up\b",
]

_ACTION_REGEX = re.compile("|".join(ACTION_PATTERNS), re.IGNORECASE)


def ensure_nltk_data():
    """Download required NLTK tokenizer data if not already present."""
    for resource in ("punkt", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{resource}")
        except LookupError:
            nltk.download(resource, quiet=True)


def summarize_text(text: str, sentence_count: int = 5) -> str:
    """
    Produce an extractive summary of the text using the LSA algorithm.

    Args:
        text: the full transcript text.
        sentence_count: how many sentences to include in the summary.

    Returns:
        The summary as a single string (sentences joined with spaces).
    """
    ensure_nltk_data()

    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary_sentences = summarizer(parser.document, sentence_count)

    return " ".join(str(sentence) for sentence in summary_sentences)


def extract_action_items(text: str) -> list[str]:
    """
    Find sentences that look like action items based on keyword patterns.

    This is intentionally simple (no AI model) - it flags sentences
    containing common task/commitment language, so you can quickly scan
    a transcript for things that need follow-up.

    Args:
        text: the full transcript text.

    Returns:
        A list of sentences flagged as potential action items.
    """
    ensure_nltk_data()

    sentences = nltk.sent_tokenize(text)
    action_items = [s.strip() for s in sentences if _ACTION_REGEX.search(s)]

    return action_items


def build_report(transcript_text: str, summary: str, action_items: list[str], source_name: str) -> str:
    """Assemble the final Markdown report."""
    lines = [
        f"# Meeting summary - {source_name}",
        "",
        "## Summary",
        "",
        summary,
        "",
        "## Action items",
        "",
    ]

    if action_items:
        for item in action_items:
            lines.append(f"- [ ] {item}")
    else:
        lines.append("_No action items detected._")

    lines += [
        "",
        "## Full transcript",
        "",
        "<details>",
        "<summary>Click to expand</summary>",
        "",
        transcript_text,
        "",
        "</details>",
        "",
    ]

    return "\n".join(lines)


def save_report(report: str, transcript_path: str, output_dir: str = "output") -> str:
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(transcript_path))[0]
    base_name = base_name.replace("_transcript", "")
    output_path = os.path.join(output_dir, f"{base_name}_summary.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/summarize.py <transcript_file.txt>")
        sys.exit(1)

    transcript_path = sys.argv[1]

    if not os.path.exists(transcript_path):
        print(f"Error: file not found: {transcript_path}")
        sys.exit(1)

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    print("Summarizing transcript...")
    summary = summarize_text(transcript_text)

    print("Extracting action items...")
    action_items = extract_action_items(transcript_text)

    source_name = os.path.splitext(os.path.basename(transcript_path))[0]
    report = build_report(transcript_text, summary, action_items, source_name)
    output_path = save_report(report, transcript_path)

    print("\n--- Summary ---")
    print(summary)
    print(f"\n--- Action items ({len(action_items)}) ---")
    for item in action_items:
        print(f"- {item}")
    print(f"\nFull report saved to: {output_path}")


if __name__ == "__main__":
    main()
