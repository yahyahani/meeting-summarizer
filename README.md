# Meeting Summarizer

A fully local tool that turns audio recordings (meetings, lectures, voice
memos) into a clean summary with extracted action items - no API keys, no
cloud services, no data leaving your machine.

It uses [OpenAI's Whisper](https://github.com/openai/whisper) for speech-to-text
and a local extractive summarization algorithm for the summary, so everything
runs offline on your own CPU.

## What it does

```
audio file (.mp3 / .wav / .m4a)
        │
        ▼
  Whisper (local)  ───►  full transcript
        │
        ▼
  Summarizer       ───►  summary + action items
        │
        ▼
  Markdown report  ───►  output/your_meeting_summary.md
```

Given an audio file, it produces a Markdown report containing:

- A short summary of the key points
- A checklist of detected action items
- The full transcript (collapsible, for reference)

## Features

- **Fully local and private** - no internet connection or API key required
  once the Whisper model is downloaded
- **One-command pipeline** - transcription and summarization in a single
  CLI call
- **Configurable** - choose the Whisper model size, summary length, and
  output location
- **Tested** - core logic covered by a pytest suite

## Installation

Requires Python 3.10+ and [ffmpeg](https://ffmpeg.org) (used by Whisper to
decode audio).

```bash
# Clone the repository
git clone https://github.com/yahyahani/meeting-summarizer.git
cd meeting-summarizer

# Install ffmpeg (macOS)
brew install ffmpeg

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the full pipeline on an audio file:

```bash
python3 src/pipeline.py sample_audio/meeting.m4a
```

This will:
1. Transcribe the audio locally with Whisper
2. Summarize the transcript
3. Extract action items
4. Save a Markdown report to `output/`

### Options

| Flag | Default | Description |
|---|---|---|
| `--model` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large`. Bigger = more accurate, slower, more RAM. |
| `--sentences` | `5` | Number of sentences to include in the summary. |
| `--output-dir` | `output` | Directory where the transcript and report are saved. |
| `--keep-transcript` / `--no-keep-transcript` | `--keep-transcript` | Whether to also save the raw transcript as a `.txt` file. |

Example with a larger, more accurate model:

```bash
python3 src/pipeline.py sample_audio/meeting.m4a --model small --sentences 8
```

See all options:

```bash
python3 src/pipeline.py --help
```

### Running stages individually

The pipeline is built from two independent stages, which can also be run on
their own:

```bash
# Stage 1: audio -> transcript only
python3 src/transcribe.py sample_audio/meeting.m4a

# Stage 2: transcript -> summary + action items
python3 src/summarize.py output/meeting_transcript.txt
```

## Running the tests

```bash
python3 -m pytest tests/ -v
```

The test suite covers the summarization, action-item extraction, and
report-building logic. It runs fully offline in under a second, since it
doesn't depend on Whisper or real audio files.

## Project structure

```
meeting-summarizer/
├── src/
│   ├── transcribe.py   # Stage 1: audio -> text (Whisper)
│   ├── summarize.py    # Stage 2: text -> summary + action items
│   └── pipeline.py     # CLI entry point combining both stages
├── tests/
│   ├── test_transcribe.py
│   └── test_summarize.py
├── sample_audio/       # put your audio files here
├── output/             # generated transcripts and reports land here
├── conftest.py         # pytest path configuration
└── requirements.txt
```

## How action items are detected

Action items are found using pattern matching on common task/commitment
phrases (e.g. "need to", "follow up with", "by Friday", "deadline"), rather
than a separate AI model. It's intentionally simple, fast, and fully
transparent - you can see exactly why a sentence was flagged by checking
`ACTION_PATTERNS` in `src/summarize.py`.

## Notes on accuracy

Transcription quality depends on the Whisper model size and audio quality.
The default `base` model is fast but can struggle with background noise or
unclear audio. If your transcripts come out garbled, try a larger model:

```bash
python3 src/pipeline.py sample_audio/meeting.m4a --model medium
```

## License

MIT
