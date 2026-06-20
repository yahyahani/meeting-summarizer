"""
Tests for src/pdf_report.py - PDF generation with multi-language font
support. These build real (small) PDF files and check that they were
created successfully and contain content, without needing Whisper or
real audio.
"""

import os

from pdf_report import build_pdf_report


class TestBuildPdfReport:
    def test_creates_a_pdf_file(self, tmp_path):
        output_path = tmp_path / "report.pdf"
        build_pdf_report(
            output_path=str(output_path),
            source_name="test_meeting",
            summary="This is a short summary.",
            action_items=["Do the thing.", "Send the email."],
            transcript="This is the full transcript text.",
            language_code="en",
            language_name="English",
        )

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_pdf_starts_with_valid_header(self, tmp_path):
        # A real PDF file always starts with "%PDF-" - this is a quick
        # sanity check that we produced an actual PDF, not garbage.
        output_path = tmp_path / "report.pdf"
        build_pdf_report(
            output_path=str(output_path),
            source_name="test_meeting",
            summary="Summary text.",
            action_items=[],
            transcript="Transcript text.",
            language_code="en",
            language_name="English",
        )

        with open(output_path, "rb") as f:
            header = f.read(5)

        assert header == b"%PDF-"

    def test_handles_no_action_items(self, tmp_path):
        output_path = tmp_path / "report.pdf"
        # Should not raise even with an empty action items list.
        build_pdf_report(
            output_path=str(output_path),
            source_name="empty_test",
            summary="Summary.",
            action_items=[],
            transcript="Transcript.",
            language_code="en",
            language_name="English",
        )
        assert output_path.exists()

    def test_builds_arabic_pdf_without_error(self, tmp_path):
        # Arabic uses a different font and requires text reshaping - this
        # is the riskiest path in the module, so it gets its own test.
        output_path = tmp_path / "report_ar.pdf"
        build_pdf_report(
            output_path=str(output_path),
            source_name="arabic_test",
            summary="يجب أن ننهي التقرير يوم الجمعة.",
            action_items=["سارة يجب أن تتحقق من الأرقام."],
            transcript="يجب أن ننهي التقرير يوم الجمعة.",
            language_code="ar",
            language_name="Arabic",
        )
        assert output_path.exists()
        with open(output_path, "rb") as f:
            assert f.read(5) == b"%PDF-"

    def test_builds_chinese_pdf_without_error(self, tmp_path):
        output_path = tmp_path / "report_zh.pdf"
        build_pdf_report(
            output_path=str(output_path),
            source_name="chinese_test",
            summary="我们需要在星期五之前完成报告。",
            action_items=["莎拉必须检查预算数字。"],
            transcript="我们需要在星期五之前完成报告。",
            language_code="zh",
            language_name="Chinese",
        )
        assert output_path.exists()
        with open(output_path, "rb") as f:
            assert f.read(5) == b"%PDF-"

    def test_returns_output_path(self, tmp_path):
        output_path = tmp_path / "report.pdf"
        result = build_pdf_report(
            output_path=str(output_path),
            source_name="test",
            summary="Summary.",
            action_items=[],
            transcript="Transcript.",
            language_code="en",
            language_name="English",
        )
        assert result == str(output_path)
