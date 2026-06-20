"""
Stage 1: Audio -> Text transcription using local Whisper.

Usage:
    python src/transcribe.py path/to/audio.mp3
"""

import sys
import os
import whisper


# Maps Whisper's language codes to readable names for display in the UI.
LANGUAGE_NAMES = {
    "en": "English", "nl": "Dutch", "ar": "Arabic", "es": "Spanish",
    "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese",
    "ru": "Russian", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "tr": "Turkish", "pl": "Polish", "sv": "Swedish", "uk": "Ukrainian",
    "hi": "Hindi", "id": "Indonesian", "fi": "Finnish", "no": "Norwegian",
    "da": "Danish", "el": "Greek", "he": "Hebrew", "ur": "Urdu",
    "fa": "Persian", "vi": "Vietnamese", "th": "Thai", "cs": "Czech",
}


def transcribe_audio_full(audio_path: str, model_size: str = "base") -> dict:
    """
    Transcribe an audio file using Whisper and return the full result,
    including the auto-detected source language.

    Whisper detects the spoken language automatically - this is not a
    setting you choose, it's identified from the audio itself. The
    transcript is returned in that same language (Whisper transcribes,
    it does not translate, unless explicitly told to).

    Args:
        audio_path: path to the audio file (.mp3, .wav, .m4a, etc.)
        model_size: whisper model size - "tiny", "base", "small", "medium", "large"

    Returns:
        A dict with keys: "text" (str), "language" (str, e.g. "en"),
        "language_name" (str, e.g. "English").
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    print(f"Loading Whisper model '{model_size}'... (first run downloads the model)")
    model = whisper.load_model(model_size)

    print(f"Transcribing: {audio_path}")
    result = model.transcribe(audio_path)

    language_code = result.get("language", "en")
    language_name = LANGUAGE_NAMES.get(language_code, language_code.upper())

    return {
        "text": result["text"],
        "language": language_code,
        "language_name": language_name,
    }


def transcribe_audio(audio_path: str, model_size: str = "base") -> str:
    """
    Transcribe an audio file to text using OpenAI's Whisper, running locally.

    Kept for backwards compatibility with existing callers that only need
    the transcript text. Use transcribe_audio_full() if you also need the
    detected language.

    Args:
        audio_path: path to the audio file (.mp3, .wav, .m4a, etc.)
        model_size: whisper model size - "tiny", "base", "small", "medium", "large"
                    bigger = more accurate but slower and more RAM-hungry.

    Returns:
        The full transcript as a single string.
    """
    return transcribe_audio_full(audio_path, model_size)["text"]


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
