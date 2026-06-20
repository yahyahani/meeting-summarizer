"""
Web interface for the meeting summarizer, built with Flask.

Reuses the exact same transcribe_audio / summarize_text / extract_action_items
functions used by the CLI pipeline (src/pipeline.py) - this is just a
different front-end on top of the same logic.

Usage:
    python3 app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import sys
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from transcribe import transcribe_audio
from summarize import summarize_text, extract_action_items

app = Flask(__name__)

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a"}

os.makedirs(UPLOAD_DIR, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html", error=None)


@app.route("/process", methods=["POST"])
def process():
    uploaded_file = request.files.get("audio_file")
    model = request.form.get("model", "base")

    if not uploaded_file or uploaded_file.filename == "":
        return render_template("index.html", error="Please choose an audio file.")

    if not allowed_file(uploaded_file.filename):
        return render_template(
            "index.html",
            error="Unsupported file type. Please upload .mp3, .wav, or .m4a.",
        )

    filename = secure_filename(uploaded_file.filename)
    saved_path = os.path.join(UPLOAD_DIR, filename)
    uploaded_file.save(saved_path)

    try:
        transcript = transcribe_audio(saved_path, model_size=model)
    except Exception as exc:
        return render_template("index.html", error=f"Transcription failed: {exc}")

    summary = summarize_text(transcript, sentence_count=5)
    action_items = extract_action_items(transcript)
    source_name = os.path.splitext(filename)[0]

    word_count = len(transcript.split())
    # Rough estimate: average speaking pace is ~130 words/minute.
    duration_minutes = max(1, round(word_count / 130))

    return render_template(
        "results.html",
        source_name=source_name,
        summary=summary,
        action_items=action_items,
        transcript=transcript,
        word_count=word_count,
        duration_minutes=duration_minutes,
    )


if __name__ == "__main__":
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(host=host, port=port, debug=debug)
