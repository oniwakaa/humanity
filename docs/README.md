# Offline-First Privacy Journal

## Overview
A privacy-first, offline-only journaling application using local AI (Ollama + whisper.cpp) and semantic memory (Qdrant).

## Architecture
- **STT**: whisper.cpp (streaming)
- **LLM**: Ollama (User managed)
- **Memory**: Qdrant (Local Docker or embedded if possible, we assume separate service based on prompt default `http://127.0.0.1:6333`)
- **Storage**: JSON Lines (mostly) for journal entries.

## Setup
1. Create a virtual environment: `python -m venv venv`
2. Activate: `source venv/bin/activate`
3. Install: `pip install -r requirements.txt`
4. Run Wizard: `python setup_wizard.py`

## Privacy
- No data leaves the device.
- Logs are sanitized.
