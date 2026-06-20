"""
Pipeline + CLI: ties transcription (Stage 1) and summarization (Stage 2)
together into a single command.

Usage:
    python src/pipeline.py sample_audio/meeting.m4a
    python src/pipeline.py sample_audio/meeting.m4a --model small
    python src/pipeline.py sample_audio/meeting.m4a --model small --output-dir results
    python src/pipeline.py sample_audio/meeting.m4a --sentences 8 --keep-transcript
"""

import os
import sys

import click

from transcribe import transcribe_audio, save_transcript
from summarize import summarize_text, extract_action_items, build_report, save_report


MODEL_CHOICES = ["tiny", "base", "small", "medium", "large"]


@click.command()
@click.argument("audio_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--model",
    type=click.Choice(MODEL_CHOICES),
    default="base",
    show_default=True,
    help="Whisper model size. Bigger = more accurate, slower, more RAM.",
)
@click.option(
    "--sentences",
    type=int,
    default=5,
    show_default=True,
    help="Number of sentences to include in the summary.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False),
    default="output",
    show_default=True,
    help="Directory where the transcript and summary report are saved.",
)
@click.option(
    "--keep-transcript/--no-keep-transcript",
    default=True,
    show_default=True,
    help="Whether to also save the raw transcript as a .txt file.",
)
def run(audio_path: str, model: str, sentences: int, output_dir: str, keep_transcript: bool):
    """
    Transcribe AUDIO_PATH locally with Whisper, then summarize it and
    extract action items into a Markdown report - all in one command.
    """
    transcript_text = transcribe_audio(audio_path, model_size=model)

    if keep_transcript:
        transcript_path = save_transcript(transcript_text, audio_path, output_dir=output_dir)
        click.echo(f"Transcript saved to: {transcript_path}")

    click.echo("Summarizing transcript...")
    summary = summarize_text(transcript_text, sentence_count=sentences)

    click.echo("Extracting action items...")
    action_items = extract_action_items(transcript_text)

    source_name = os.path.splitext(os.path.basename(audio_path))[0]
    report = build_report(transcript_text, summary, action_items, source_name)
    report_path = save_report(report, f"{source_name}_transcript.txt", output_dir=output_dir)

    click.echo("\n--- Summary ---")
    click.echo(summary)
    click.echo(f"\n--- Action items ({len(action_items)}) ---")
    for item in action_items:
        click.echo(f"- {item}")

    click.echo(f"\nFull report saved to: {report_path}")


if __name__ == "__main__":
    run()
