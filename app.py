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
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from transcribe import transcribe_audio_full, save_transcript
from summarize import summarize_text, extract_action_items
from pdf_report import build_pdf_report

app = Flask(__name__)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


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
        # Whisper auto-detects the spoken language from the audio itself -
        # this isn't something the user selects, it's identified during
        # transcription, and the transcript comes back in that language.
        result = transcribe_audio_full(saved_path, model_size=model)
    except Exception as exc:
        return render_template("index.html", error=f"Transcription failed: {exc}")

    transcript = result["text"]
    language_code = result["language"]
    language_name = result["language_name"]

    # Save the full transcript to disk so it can be downloaded as a .txt
    # file from the results page (same helper the CLI pipeline uses).
    transcript_path = save_transcript(transcript, filename, output_dir=OUTPUT_DIR)
    transcript_filename = os.path.basename(transcript_path)

    summary = summarize_text(transcript, sentence_count=5)
    action_items = extract_action_items(transcript)
    source_name = os.path.splitext(filename)[0]

    # Also build a PDF report (summary + action items + transcript) using
    # a font appropriate for the detected language's script.
    pdf_filename = f"{source_name}_report.pdf"
    pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
    build_pdf_report(
        output_path=pdf_path,
        source_name=source_name,
        summary=summary,
        action_items=action_items,
        transcript=transcript,
        language_code=language_code,
        language_name=language_name,
    )

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
        transcript_filename=transcript_filename,
        pdf_filename=pdf_filename,
        language_name=language_name,
    )


@app.route("/download/<path:filename>")
def download_transcript(filename):
    # secure_filename strips any path traversal characters; combined with
    # send_from_directory (which itself blocks ../ escapes), this only
    # ever serves files that live inside OUTPUT_DIR.
    safe_name = secure_filename(filename)
    full_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.isfile(full_path):
        abort(404)
    return send_from_directory(OUTPUT_DIR, safe_name, as_attachment=True)


if __name__ == "__main__":
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(host=host, port=port, debug=debug)
