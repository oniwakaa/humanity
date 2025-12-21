# Agent.MD — Build Humanity (Local AI Diary) Coding Agent Guide

> This file is the **single source of truth** for how an AI coding agent should work on the Build Humanity backend.  
> It is optimized for offline-first development with strict local-only dependencies (Ollama + Qdrant + local STT). [web:60][page:1]

## Mission
Build a backend-only MVP for **Build Humanity**, a fully local AI-first diary with:
- File-first canonical storage (no cloud).
- Qdrant semantic memory for retrieval.
- Existing Ollama server over HTTP for generation + embeddings.
- Near real-time local speech-to-text (STT) with partial updates and finalized commits. [page:1][page:5][page:6]

## Non-negotiables (SHALL)
- The system SHALL make **zero cloud calls** at runtime (including analytics, crash reporting, model downloads).  
- The system SHALL treat Ollama as an **external local dependency**: connect via `ollama_base_url`, never install/manage/replace Ollama. [page:1]  
- The system SHALL validate Ollama connectivity and model availability via `GET /api/tags` before enabling AI features. [page:2]  
- The system SHALL default-suggest `http://127.0.0.1:11434` for Ollama base URL and allow override. [page:1][web:39]  
- The system SHALL support separate models: `chat_model_name` (user-provided) and `embed_model_name` (default suggestion `mxbai-embed-large:latest`, must be installed by user). [web:21][page:2]  
- The STT system SHALL emit partial transcript updates at a human-usable cadence (~0.5–2.0s) and commit final segments on silence/time-window boundaries. [page:6]  
- The system SHALL maintain two transcript states: `partial_ephemeral` and `final_committed`. [page:7]

## What to build (backend scope)
### Core modules (must exist)
- Settings & Connection Wizard (Ollama + Qdrant + STT)
- Ollama Connector (list models, embeddings, generation)
- Audio Capture & Buffering
- STT Engine (default whisper.cpp streaming)
- Journal Storage (file-first canonical store)
- Qdrant Memory Layer (chunk→embed→upsert; search→context pack; delete consistency)
- Orchestrator (feature workflows + retrieval + prompt policy)
- Safety & Consent Guardrails (non-diagnostic language, user control)
- Telemetry/Logging (local-only, privacy-preserving)

### Features (minimum)
- Survey (Big Five style, non-clinical)
- Your Story (voice/text, follow-ups)
- Daily Deep Questions (MCQ/Likert/open)
- Free Diary (voice/text, optional reflection/summaries)

## Architecture rules (agent behavior)
- Prefer **boring, implementable** solutions. Avoid frameworks, microservices, or complex event buses unless strictly needed.
- Prefer **append-only** and crash-resilient writes for STT final segments.
- Prefer **queues as files** (JSONL) over full databases.
- Only introduce SQLite if there is a concrete MVP need (e.g., atomic scheduling/querying that cannot be achieved with file-first indexing).

## Dependency boundaries
### Ollama boundary
- The backend may call only the configured `ollama_base_url` and SHALL treat it as untrusted input.
- Use `/api/tags` to confirm reachability and model tags. [page:2]
- If the embed model tag is missing, the app SHALL guide the user to install it (e.g., “run `ollama pull ...` on the Ollama host”), but SHALL NOT do it itself. [web:21]

### Qdrant boundary
- Qdrant is local-only and stores:
  - vectors
  - payload metadata (entry_id, chunk_id, feature_type, timestamps, tags)
- Files are canonical; Qdrant is a derived index (rebuildable).

### STT boundary
- Default to whisper.cpp streaming approach; keep engine pluggable to allow Vosk later.
- Partial outputs are UI-facing only; final commits are canonical. [page:6][page:7]

## Degraded-mode policy (must implement)
- If Ollama is unreachable: journaling + STT still work; embeddings/generation are disabled and queued until recovery. [page:1][page:2]
- If `/api/tags` works but model tags invalid: AI features remain disabled until corrected. [page:2]
- If Qdrant is down: still store entries; queue embeddings; semantic search disabled.
- If STT fails: fall back to text-only entry; never block saving.

## Data conventions (no SQL schemas here)
- File-first canonical store:
  - One folder per entry (recommended) or one file per entry (acceptable).
  - Store committed transcript blocks as immutable append-only records.
- Chunking:
  - Chunk on paragraph boundaries or committed STT blocks.
  - Keep chunk IDs stable and content-hash to avoid re-embedding storms.
- Deletion:
  - Deleting an entry MUST delete associated Qdrant vectors (by entry_id).

## Implementation workflow (how the agent should work)
1. Start every task by writing a short plan (5–10 bullets).
2. Make changes in small, reviewable steps.
3. Add minimal tests or runnable checks where feasible (especially for:
   - settings validation
   - queue replay/recovery
   - chunking determinism
   - deletion consistency)
4. Never add new dependencies without justification.
5. When uncertain, ask for clarification instead of inventing requirements.

## Acceptance checklist (agent must self-verify)
- [ ] Wizard validates Ollama via `/api/tags` and checks both model tags. [page:2]
- [ ] Default suggestions: `http://127.0.0.1:11434` and `mxbai-embed-large:latest`. [page:1][web:21]
- [ ] STT produces partials every ~0.5–2.0 seconds in normal conditions. [page:6]
- [ ] STT commits final segments as immutable blocks; partials never persisted. [page:7]
- [ ] File store is canonical; Qdrant is derivable; export works without Qdrant.
- [ ] Ollama down does not block journaling; queues drain after recovery. [page:2]
- [ ] Logs are local-only and do not store raw diary content by default.

## “Things to look out for” (minimum set)
- STT partial vs final text can diverge; avoid duplication by design. [page:7]
- Whisper streaming cadence vs CPU load tradeoff (0.5s step is heavier). [page:6]
- Silence/VAD tuning: over-segmentation vs latency.
- Long recording sessions can drift latency; enforce time windows.
- Audio device hot-swap and permissions.
- Ollama base URL mistakes; always validate with `/api/tags`. [page:2]
- Model tags must match exactly what `/api/tags` returns. [page:2]
- Ollama timeouts and restarts mid-request; retries must be bounded. [page:1]
- Embed model dimension changes require reindex strategy.
- Qdrant delete consistency (avoid orphan vectors).
- File crash safety: append-only writes + recovery scans.
- Local logs/crash dumps must not leak sensitive text/audio.

## Communication style
- Keep output concise and operational: describe files to change, functions to add, and edge cases handled.
- Do not propose cloud services, remote telemetry, or hosted LLMs.
- If OS/CPU/RAM/GPU is unknown, pick conservative defaults and document tunables.

## Open questions the agent should ask early (if not specified)
- Target OS (macOS/Linux/Windows) and packaging expectations (Docker vs native).
- Preferred backend language/runtime.
- Whether Qdrant runs embedded or as a separate local service.
- Whether audio capture is handled by backend daemon or by the client.
