"""
Tests for src/summarize.py - summarization, action item extraction,
and report building. These run fully offline and fast (no Whisper,
no real audio needed).
"""

import os

from summarize import (
    summarize_text,
    extract_action_items,
    build_report,
    save_report,
)


SAMPLE_TEXT = (
    "Okay so let's get started with the meeting. "
    "Today we need to discuss the Q3 roadmap and the budget situation. "
    "The marketing team has been working on the new campaign for two weeks. "
    "We should review the analytics before making any final decisions. "
    "John, you need to follow up with the design team about the new mockups by Friday. "
    "The budget is currently at eighty percent utilization. "
    "I think we have to make sure the client presentation is ready before the deadline next Wednesday. "
    "Sarah will send the updated timeline to everyone after this call. "
    "Let's also talk about the hiring situation for the engineering team. "
    "We need three more developers by end of quarter. "
    "The current sprint is going well overall. "
    "I will schedule a follow-up meeting with the infrastructure team next week."
)


class TestSummarizeText:
    def test_returns_a_nonempty_string(self):
        summary = summarize_text(SAMPLE_TEXT, sentence_count=3)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_respects_sentence_count(self):
        # The LSA summarizer can't always return more sentences than
        # requested, but it should never wildly exceed the limit either.
        summary = summarize_text(SAMPLE_TEXT, sentence_count=2)
        # Rough sentence count check via period count.
        sentence_count = summary.count(".")
        assert sentence_count <= 3  # small tolerance for abbreviations etc.

    def test_empty_text_does_not_crash(self):
        # An empty transcript should not raise an exception.
        summary = summarize_text("", sentence_count=3)
        assert summary == ""


class TestExtractActionItems:
    def test_detects_known_action_phrases(self):
        items = extract_action_items(SAMPLE_TEXT)
        joined = " ".join(items)
        assert "follow up with the design team" in joined
        assert "three more developers" in joined

    def test_ignores_generic_sentences(self):
        items = extract_action_items(SAMPLE_TEXT)
        joined = " ".join(items)
        # These should NOT be flagged - they're generic conversational
        # filler, not real action items.
        assert "let's get started with the meeting" not in joined.lower()
        assert "marketing team has been working" not in joined.lower()

    def test_no_action_items_returns_empty_list(self):
        text = "The weather was nice today. We had a good conversation."
        items = extract_action_items(text)
        assert items == []

    def test_returns_list_of_strings(self):
        items = extract_action_items(SAMPLE_TEXT)
        assert isinstance(items, list)
        assert all(isinstance(item, str) for item in items)


class TestBuildReport:
    def test_includes_all_sections(self):
        report = build_report(
            transcript_text="Full transcript text here.",
            summary="A short summary.",
            action_items=["Do the thing.", "Send the email."],
            source_name="test_meeting",
        )
        assert "# Meeting summary - test_meeting" in report
        assert "## Summary" in report
        assert "A short summary." in report
        assert "## Action items" in report
        assert "- [ ] Do the thing." in report
        assert "- [ ] Send the email." in report
        assert "## Full transcript" in report
        assert "Full transcript text here." in report

    def test_handles_no_action_items(self):
        report = build_report(
            transcript_text="Some text.",
            summary="Some summary.",
            action_items=[],
            source_name="empty_test",
        )
        assert "_No action items detected._" in report


class TestSaveReport:
    def test_creates_file_with_expected_name(self, tmp_path):
        output_dir = tmp_path / "output"
        report_text = "# Test report\n\nSome content."

        saved_path = save_report(
            report_text,
            "my_meeting_transcript.txt",
            output_dir=str(output_dir),
        )

        assert os.path.exists(saved_path)
        assert saved_path.endswith("my_meeting_summary.md")

    def test_strips_transcript_suffix_from_filename(self, tmp_path):
        output_dir = tmp_path / "output"
        saved_path = save_report(
            "content",
            "weekly_sync_transcript.txt",
            output_dir=str(output_dir),
        )
        assert "weekly_sync_summary.md" in saved_path
        # Make sure "_transcript" doesn't leak into the output filename.
        assert "transcript" not in os.path.basename(saved_path)

    def test_file_content_matches_input(self, tmp_path):
        output_dir = tmp_path / "output"
        report_text = "# My report\n\nDetailed content here."
        saved_path = save_report(report_text, "x_transcript.txt", output_dir=str(output_dir))

        with open(saved_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert content == report_text
