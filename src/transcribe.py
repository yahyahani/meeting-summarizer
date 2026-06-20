"""
Stage 1: Audio -> Text transcription using local Whisper.

Usage:
    python src/transcribe.py path/to/audio.mp3
"""

import sys
import os
import whisper


def transcribe_audio(audio_path: str, model_size: str = "base") -> str:
    """
    Transcribe an audio file to text using OpenAI's Whisper, running locally.

    Args:
        audio_path: path to the audio file (.mp3, .wav, .m4a, etc.)
        model_size: whisper model size - "tiny", "base", "small", "medium", "large"
                    bigger = more accurate but slower and more RAM-hungry.

    Returns:
        The full transcript as a single string.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    print(f"Loading Whisper model '{model_size}'... (first run downloads the model)")
    model = whisper.load_model(model_size)

    print(f"Transcribing: {audio_path}")
    result = model.transcribe(audio_path)

    return result["text"]


def save_transcript(text: str, audio_path: str, output_dir: str = "output") -> str:
    """Save the transcript next to a .txt file named after the audio file."""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_transcript.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/transcribe.py <audio_file> [model_size]")
        sys.exit(1)

    audio_path = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "base"

    transcript = transcribe_audio(audio_path, model_size)
    output_path = save_transcript(transcript, audio_path)

    print("\n--- Transcript preview ---")
    print(transcript[:300] + ("..." if len(transcript) > 300 else ""))
    print(f"\nFull transcript saved to: {output_path}")


if __name__ == "__main__":
    main()
