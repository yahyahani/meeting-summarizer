# Meeting Summarizer - Docker image
# Runs the Flask web app. Whisper, ffmpeg, and all Python dependencies
# are installed inside the container, so the only requirement on the
# host machine is Docker itself.

FROM python:3.11-slim

# ffmpeg is required by Whisper to decode audio files
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching - this layer
# only rebuilds when requirements.txt changes, not on every code edit)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Folders the app writes to at runtime
RUN mkdir -p uploads output sample_audio

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000
ENV FLASK_DEBUG=false
ENV PYTHONUNBUFFERED=1

CMD ["python3", "app.py"]
