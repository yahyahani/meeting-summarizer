"""
Web interface for the meeting summarizer, built with Flask.

Reuses the exact same transcribe_audio_full / summarize_text /
extract_action_items functions used by the CLI pipeline (src/pipeline.py)
- this is just a different front-end on top of the same logic.

Usage:
    python3 app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import sys
import time
import logging
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from transcribe import transcribe_audio_full, save_transcript
from summarize import summarize_text, extract_action_items
from pdf_report import build_pdf_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("meeting-summarizer")

app = Flask(__name__)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a"}
ALLOWED_MODELS = {"tiny", "base", "small", "medium", "large"}
MAX_UPLOAD_MB = 200
# Files older than this in uploads/ and output/ are cleaned up at the
# start of each /process request, so disk usage doesn't grow unbounded
# across repeated local use. Generous on purpose - this isn't a strict
# retention policy, just basic housekeeping.
MAX_FILE_AGE_HOURS = 24

# Reject uploads larger than this before Flask even reads the full body
# into memory - prevents a huge file from exhausting RAM or disk.
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.errorhandler(413)
def file_too_large(e):
    return render_template(
        "index.html",
        error=f"File too large. Please upload an audio file under {MAX_UPLOAD_MB}MB.",
    ), 413


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_old_files(directory: str, max_age_hours: int = MAX_FILE_AGE_HOURS) -> None:
    """
    Delete files in `directory` older than max_age_hours.

    Best-effort housekeeping for uploads/ and output/ - failures to
    remove an individual file (e.g. permissions) are logged and skipped
    rather than raised, since this should never block a real request.
    """
    cutoff = time.time() - (max_age_hours * 3600)
    try:
        entries = os.listdir(directory)
    except OSError as exc:
        logger.warning("Could not list %s for cleanup: %s", directory, exc)
        return

    for name in entries:
        if name.startswith("."):  # keep .gitkeep etc.
            continue
        path = os.path.join(directory, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
                logger.info("Cleaned up old file: %s", path)
        except OSError as exc:
            logger.warning("Could not remove %s during cleanup: %s", path, exc)


@app.route("/")
def index():
    return render_template("index.html", error=None)


@app.route("/process", methods=["POST"])
def process():
    cleanup_old_files(UPLOAD_DIR)
    cleanup_old_files(OUTPUT_DIR)

    uploaded_file = request.files.get("audio_file")
    model = request.form.get("model", "base")

    if model not in ALLOWED_MODELS:
        logger.warning("Rejected request with invalid model value: %r", model)
        model = "base"

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

    if os.path.getsize(saved_path) == 0:
        os.remove(saved_path)
        return render_template("index.html", error="That file appears to be empty.")

    logger.info("Processing upload: %s (model=%s)", filename, model)

    try:
        # Whisper auto-detects the spoken language from the audio itself -
        # this isn't something the user selects, it's identified during
        # transcription, and the transcript comes back in that language.
        result = transcribe_audio_full(saved_path, model_size=model)
    except Exception as exc:
        logger.exception("Transcription failed for %s", filename)
        return render_template(
            "index.html",
            error="Transcription failed. Please check that the file is a valid audio recording.",
        )

    transcript = result["text"]
    language_code = result["language"]
    language_name = result["language_name"]

    if not transcript.strip():
        return render_template(
            "index.html",
            error="No speech was detected in that recording.",
        )

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
    try:
        build_pdf_report(
            output_path=pdf_path,
            source_name=source_name,
            summary=summary,
            action_items=action_items,
            transcript=transcript,
            language_code=language_code,
            language_name=language_name,
        )
    except Exception:
        # The PDF is a nice-to-have alongside the transcript/summary - if
        # it fails for some reason, still show the results page rather
        # than losing the whole transcription the user just waited for.
        logger.exception("PDF generation failed for %s", filename)
        pdf_filename = None

    word_count = len(transcript.split())
    # Rough estimate: average speaking pace is ~130 words/minute.
    duration_minutes = max(1, round(word_count / 130))

    logger.info(
        "Done: %s -> %d words, %d action items, language=%s",
        filename, word_count, len(action_items), language_code,
    )

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
    # Default to False: debug mode exposes full Python stack traces and
    # an interactive debugger to anyone who can reach the server, which
    # is fine on localhost during development but should never be the
    # silent default. Opt in explicitly with FLASK_DEBUG=true if needed.
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info("Starting Meeting Summarizer on %s:%s (debug=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug)
