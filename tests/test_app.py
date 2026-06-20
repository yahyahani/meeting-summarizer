"""
Tests for app.py - Flask request validation and file cleanup logic.
These don't require Whisper or real audio; transcription is mocked out
where needed so the tests run fast and offline.
"""

import io
import os
import time

import pytest

from app import app, cleanup_old_files, allowed_file, ALLOWED_MODELS


class TestAllowedFile:
    def test_accepts_known_extensions(self):
        assert allowed_file("meeting.mp3")
        assert allowed_file("meeting.wav")
        assert allowed_file("meeting.m4a")

    def test_rejects_unknown_extensions(self):
        assert not allowed_file("document.pdf")
        assert not allowed_file("script.exe")
        assert not allowed_file("no_extension")


class TestProcessRoute:
    def test_no_file_shows_error(self):
        with app.test_client() as client:
            resp = client.post("/process", data={})
            assert b"choose an audio file" in resp.data.lower()

    def test_wrong_file_type_shows_error(self):
        with app.test_client() as client:
            resp = client.post(
                "/process",
                data={"audio_file": (io.BytesIO(b"data"), "document.pdf")},
                content_type="multipart/form-data",
            )
            assert b"unsupported file type" in resp.data.lower()

    def test_empty_file_shows_error(self):
        with app.test_client() as client:
            resp = client.post(
                "/process",
                data={"audio_file": (io.BytesIO(b""), "empty.wav")},
                content_type="multipart/form-data",
            )
            assert b"empty" in resp.data.lower()

    def test_invalid_model_falls_back_to_base(self, monkeypatch):
        captured = {}

        def fake_transcribe(path, model_size="base"):
            captured["model_size"] = model_size
            return {"text": "Hello world.", "language": "en", "language_name": "English"}

        monkeypatch.setattr("app.transcribe_audio_full", fake_transcribe)

        with app.test_client() as client:
            client.post(
                "/process",
                data={
                    "audio_file": (io.BytesIO(b"fake bytes"), "test.wav"),
                    "model": "not-a-real-model",
                },
                content_type="multipart/form-data",
            )

        assert captured["model_size"] == "base"

    def test_no_speech_detected_shows_error(self, monkeypatch):
        def fake_transcribe(path, model_size="base"):
            return {"text": "   ", "language": "en", "language_name": "English"}

        monkeypatch.setattr("app.transcribe_audio_full", fake_transcribe)

        with app.test_client() as client:
            resp = client.post(
                "/process",
                data={"audio_file": (io.BytesIO(b"fake bytes"), "silent.wav")},
                content_type="multipart/form-data",
            )

        assert b"no speech" in resp.data.lower()

    def test_transcription_failure_shows_friendly_error(self, monkeypatch):
        def fake_transcribe(path, model_size="base"):
            raise RuntimeError("ffmpeg exploded")

        monkeypatch.setattr("app.transcribe_audio_full", fake_transcribe)

        with app.test_client() as client:
            resp = client.post(
                "/process",
                data={"audio_file": (io.BytesIO(b"fake bytes"), "bad.wav")},
                content_type="multipart/form-data",
            )

        # Internal exception details should NOT leak to the user.
        assert b"ffmpeg exploded" not in resp.data
        assert b"transcription failed" in resp.data.lower()


class TestCleanupOldFiles:
    def test_removes_files_older_than_max_age(self, tmp_path):
        old_file = tmp_path / "old.txt"
        old_file.write_text("old")
        old_time = time.time() - (25 * 3600)
        os.utime(old_file, (old_time, old_time))

        cleanup_old_files(str(tmp_path), max_age_hours=24)

        assert not old_file.exists()

    def test_keeps_recent_files(self, tmp_path):
        new_file = tmp_path / "new.txt"
        new_file.write_text("new")

        cleanup_old_files(str(tmp_path), max_age_hours=24)

        assert new_file.exists()

    def test_keeps_dotfiles_regardless_of_age(self, tmp_path):
        dotfile = tmp_path / ".gitkeep"
        dotfile.write_text("")
        old_time = time.time() - (100 * 3600)
        os.utime(dotfile, (old_time, old_time))

        cleanup_old_files(str(tmp_path), max_age_hours=24)

        assert dotfile.exists()

    def test_does_not_raise_for_missing_directory(self):
        # Should log and return quietly, not crash the request.
        cleanup_old_files("/nonexistent/path/xyz", max_age_hours=24)
