"""
Tests for src/transcribe.py - only the parts that don't require an actual
audio file or running Whisper itself (that's covered by manual testing,
since it needs real audio and downloads a multi-hundred-MB model).
"""

import os
import pytest

from transcribe import transcribe_audio, save_transcript


class TestTranscribeAudioValidation:
    def test_raises_for_missing_file(self):
        with pytest.raises(FileNotFoundError):
            transcribe_audio("this_file_does_not_exist.mp3")


class TestSaveTranscript:
    def test_creates_file_with_expected_name(self, tmp_path):
        output_dir = tmp_path / "output"
        saved_path = save_transcript(
            "Hello, this is a transcript.",
            "my_recording.m4a",
            output_dir=str(output_dir),
        )

        assert os.path.exists(saved_path)
        assert saved_path.endswith("my_recording_transcript.txt")

    def test_file_content_matches_input(self, tmp_path):
        output_dir = tmp_path / "output"
        text = "This is the exact transcript text."
        saved_path = save_transcript(text, "test.mp3", output_dir=str(output_dir))

        with open(saved_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert content == text

    def test_creates_output_dir_if_missing(self, tmp_path):
        output_dir = tmp_path / "brand_new_folder"
        assert not output_dir.exists()

        save_transcript("text", "file.mp3", output_dir=str(output_dir))

        assert output_dir.exists()
