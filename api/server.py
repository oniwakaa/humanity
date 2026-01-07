from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager

from settings.manager import SettingsManager
from orchestrator.engine import Orchestrator
from orchestrator.background import BackgroundWorker

# --- Dependency Injection / Global State ---
settings_mgr = SettingsManager()

# Global State
orchestrator: Optional[Orchestrator] = None
worker: Optional[BackgroundWorker] = None

# Initialize if config exists
if settings_mgr.exists():
    try:
        orchestrator = Orchestrator(settings_mgr)
        worker = BackgroundWorker(orchestrator)
    except Exception as e:
        print(f"Failed to initialize orchestrator: {e}")

def require_orchestrator():
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not configured. Please complete setup.")
    return orchestrator

from api.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db() # Create tables
    if worker:
        task = asyncio.create_task(worker.run())
    else:
        task = None
    yield
    # Shutdown
    if worker:
        worker.stop()
    if task:
        await task

app = FastAPI(title="Humanity API", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class SetupRequest(BaseModel):
    # App Config
    ollama_url: str
    chat_model: str
    embed_model: str
    stt_path: str

    # User Profile
    # User Profile
    profile: Dict[str, Any]

class EntryCreate(BaseModel):
    text: str
    tags: Optional[List[str]] = []

class EntryResponse(BaseModel):
    id: str
    message: str

class ReflectionRequest(BaseModel):
    entry_id: str

class DailySubmission(BaseModel):
    cycle_id: str
    answers: List[Dict[str, Any]]

class ModelStatus(BaseModel):
    name: str
    status: str # "missing", "downloading", "ready"
    progress: Optional[float] = 0.0
    detail: Optional[str] = ""

# --- Global State for Models ---
model_state: Dict[str, Dict[str, Any]] = {}

async def pull_model_task(model_name: str):
    global model_state
    model_state[model_name] = {"status": "downloading", "progress": 0.0, "detail": "Starting..."}
    
    # Create temp client if orch not ready
    from connectors.ollama import OllamaClient
    client = orchestrator.ollama if orchestrator else OllamaClient()
    
    try:
        iterator = client.pull_model(model_name)
        for progress in iterator:
            # progress format from Ollama: {"status": "pulling...", "digest": "...", "total": 123, "completed": 12}
            status_text = progress.get("status", "")
            total = progress.get("total", 0)
            completed = progress.get("completed", 0)
            
            pct = 0.0
            if total > 0:
                pct = (completed / total) * 100
            
            detail = status_text
            
            if status_text == "success":
                model_state[model_name] = {"status": "ready", "progress": 100.0, "detail": "Ready"}
            else:
                model_state[model_name] = {"status": "downloading", "progress": pct, "detail": detail}
            
            await asyncio.sleep(0.1) # Yield to event loop
            
        # Final check
        model_state[model_name] = {"status": "ready", "progress": 100.0, "detail": "Ready"}
        
    except Exception as e:
        print(f"Error pulling model {model_name}: {e}")
        model_state[model_name] = {"status": "error", "progress": 0.0, "detail": str(e)}

# --- Endpoints ---

@app.get("/setup/status")
def get_setup_status():
    """Returns whether the backend is configured."""
    return {
        "is_configured": settings_mgr.exists(),
        "config_path": str(settings_mgr.config_path)
    }

@app.get("/api/models")
def get_models_status():
    """Returns status of required models."""
    # List of required models
    required = ["hf.co/unsloth/SmolLM3-3B-GGUF:Q4_K_M", "mxbai-embed-large:latest"]
    
    # Check actual presence
    from connectors.ollama import OllamaClient
    client = orchestrator.ollama if orchestrator else OllamaClient()
    
    try:
        installed = client.list_models()
        # Clean names (remove :latest if needed or match exact)
        # Ollama list_models returns full names e.g. "llama3.2:latest"
        
        results = []
        for req in required:
            # Check if downloading
            if req in model_state and model_state[req]["status"] == "downloading":
                results.append({
                    "name": req,
                    "status": "downloading",
                    "progress": model_state[req]["progress"],
                    "detail": model_state[req]["detail"]
                })
                continue
            
            # Check if installed (fuzzy match)
            is_installed = any(req in m for m in installed)
            if is_installed:
                 # Update ready state if it was downloading
                 if req in model_state and model_state[req]["status"] == "downloading":
                     model_state[req] = {"status": "ready", "progress": 100.0, "detail": "Ready"}
                     
                 results.append({"name": req, "status": "ready", "progress": 100.0, "detail": "Ready"})
            else:
                 results.append({"name": req, "status": "missing", "progress": 0.0, "detail": "Not installed"})
                 
        return results
    except Exception as e:
        # If ollama unreachable
        return [{"name": m, "status": "error", "detail": str(e)} for m in required]

class PullRequest(BaseModel):
    name: str

@app.post("/api/models/pull")
def trigger_pull_model(req: PullRequest, bg_tasks: BackgroundTasks):
    # Check if already downloading
    if req.name in model_state and model_state[req.name]["status"] == "downloading":
        return {"status": "already_downloading"}
    
    bg_tasks.add_task(pull_model_task, req.name)
    return {"status": "started"}

@app.post("/setup/complete")
def complete_setup(req: SetupRequest):
    """
    Saves the configuration and user profile.
    This replaces the CLI setup_wizard.py flow.
    """
    from settings.config_model import AppConfig, OllamaConfig, STTConfig
    
    # 1. Save Config
    config = AppConfig(
        ollama=OllamaConfig(
            base_url=req.ollama_url,
            chat_model=req.chat_model,
            embed_model=req.embed_model
        ),
        stt=STTConfig(
            model_path=req.stt_path
        ),
        storage_path="./data" # Default for MVP setup via API
    )
    
    try:
        settings_mgr.save_settings(config)
        
        # Initialize Global State
        global orchestrator, worker
        orchestrator = Orchestrator(settings_mgr)
        worker = BackgroundWorker(orchestrator)
        
        # Worker start? managed by next restart or manual?
        # For robustness in MVP, just rely on next restart or lazy init?
        # Lifespan only runs on startup.
        # We can try to manually start worker loop if needed, but risky.
        # Let's assume user refreshes or we are okay without background worker until restart.
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")
        
    # 2. Save Profile (as a journal entry for now)
    try:
        # We store the raw profile dict
        import json
        if orchestrator:
            orchestrator.process_new_entry(
                text=json.dumps(req.profile),
                feature_type="onboarding_profile",
                tags=["onboarding", "profile"]
            )
    except Exception as e:
        print(f"Warning: Failed to save profile entry: {e}")
        # We don't block setup on this
        
    return {"status": "setup_complete"}

@app.get("/health")
def health_check():
    if not orchestrator:
         return {"status": "waiting_setup", "ollama": "unknown", "qdrant": "unknown"}
    ollama_status = "ok" if orchestrator.ollama.check_health() else "error"
    qdrant_status = "ok" if orchestrator.memory.check_health() else "error"
    return {"status": "ok", "ollama": ollama_status, "qdrant": qdrant_status}

@app.post("/entry", response_model=EntryResponse, status_code=201)
def create_entry(entry: EntryCreate):
    """
    Creates a new Free Diary entry.
    """
    orch = require_orchestrator()
    if not entry.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
        
    try:
        # feature_type="free_diary"
        entry_id = orch.process_new_entry(
            text=entry.text,
            feature_type="free_diary",
            tags=entry.tags
        )
        return EntryResponse(id=entry_id, message="Entry saved and queued for indexing.")
    except Exception as e:
        # Log error in telemetry
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save entry")

@app.post("/verify")
def verify_connections():
    """
    Manually triggers a check of connections (Phase 0 logic helper).
    """
    orch = require_orchestrator()
    try:
        ollama_ok = orch.ollama.check_health()
        return {
            "ollama_reachable": ollama_ok,
            "qdrant_configured": orch.memory.check_health()
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/story/start")
def start_story_session():
    orch = require_orchestrator()
    try:
        orch.start_recording_session()
        return {"status": "started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start recording: {e}")

@app.post("/story/stop", response_model=EntryResponse)
def stop_story_session():
    orch = require_orchestrator()
    try:
        text = orch.stop_recording_session()
        if not text.strip():
             return EntryResponse(id="none", message="No text transcribed.")
             
        entry_id = orch.process_new_entry(
            text=text, 
            feature_type="your_story",
            tags=["voice", "your_story"]
        )
        return EntryResponse(id=entry_id, message="Story saved.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing story: {e}")

@app.post("/story/reflect")
def reflect_on_story(req: ReflectionRequest):
    """
    Triggers RAG-based reflection on a specific entry.
    """
    orch = require_orchestrator()
    entry = orch.journal.get_entry(req.entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
        
    # Generate reflection based on the text of the entry
    suggestion = orch.generate_reflection(entry["text"])
    return {"suggestion": suggestion}

@app.get("/survey/questions")
def get_survey_questions():
    # Survey questions don't strictly need orchestrator if just static file, 
    # but we use orchestrator.survey_manager
    orch = require_orchestrator()
    return orch.survey_manager.get_questions()

@app.get("/survey/status")
def get_survey_status():
    orch = require_orchestrator()
    # Check if profile is default
    is_completed = orch.user_profile != "Interaction Style: Neutral. New user."
    return {"completed": is_completed}

@app.post("/survey/submit")
def submit_survey(answers: Dict[str, int]):
    """
    Submits survey answers.
    Expects {q_id: score} mapping.
    """
    orch = require_orchestrator()
    import json
    
    text_payload = json.dumps(answers)
    
    try:
        entry_id = orch.process_new_entry(
            text=text_payload, 
            feature_type="survey",
            tags=["survey", "onboarding"]
        )
        
        # Force reload profile immediately (naive)
        orch.user_profile = orch._load_user_profile()
        
        return {"status": "saved", "entry_id": entry_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save survey: {e}")

@app.post("/daily/generate")
def generate_daily():
    orch = require_orchestrator()
    try:
        data = orch.generate_daily_questions()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/daily/submit")
def submit_daily(sub: DailySubmission):
    orch = require_orchestrator()
    try:
        entry_id = orch.submit_daily_answers(sub.cycle_id, sub.answers)
        return {"status": "saved", "entry_id": entry_id}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    message: str
    context: Optional[List[Dict[str, str]]] = []

@app.post("/chat")
def chat_message(req: ChatRequest):
    """
    AI-guided diary chat endpoint.
    Receives user message and conversation context, returns AI response.
    """
    orch = require_orchestrator()
    
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        # Build conversation context for the AI
        context_text = ""
        if req.context:
            for msg in req.context[-5:]:  # Last 5 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                context_text += f"{role.capitalize()}: {content}\n"
        
        # Create a reflective prompt for the diary
        prompt = f"""You are a compassionate AI journaling companion helping the user explore their thoughts and feelings.
Based on the conversation so far and the user's latest message, provide a thoughtful, brief response (2-3 sentences) that:
- Acknowledges what they've shared
- Asks a gentle follow-up question to deepen their reflection
- Uses warm, supportive language

Previous conversation:
{context_text}

User's message: {req.message}

Your response:"""
        
        # Use orchestrator's RAG Chat Logic
        response = orch.chat_session(req.message, req.context)
        return {"response": response}
    except Exception as e:
        print(f"Chat error: {e}")
        return {
            "response": "I'm here to listen. Could you tell me more about what's on your mind?"
        }

class DiarySaveRequest(BaseModel):
    transcript: List[Dict[str, str]]

class DiaryEntrySummary(BaseModel):
    id: str
    date: str
    title: str
    summary: str

@app.get("/diary/entries", response_model=List[DiaryEntrySummary])
def get_diary_entries(limit: int = 20, offset: int = 0):
    """
    Fetches diary entry summaries for the Diary Book UI.
    Returns entries with feature_type='open_diary', transformed to summary format.
    """
    orch = require_orchestrator()
    
    try:
        # Use DBManager directly for filtered query
        from api.database import SessionLocal
        from api.models import Entry
        
        db = SessionLocal()
        try:
            entries = (
                db.query(Entry)
                .filter(Entry.feature_type == "open_diary")
                .order_by(Entry.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            
            summaries = []
            for entry in entries:
                # Sanitize: remove <think>...</think> tags from stored content
                import re
                def sanitize_think_tags(text: str) -> str:
                    return re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE).strip()
                
                clean_text = sanitize_think_tags(entry.text)
                
                # Extract title from first line, summary from rest
                lines = clean_text.split('\n', 1)
                title = lines[0][:50] if lines else "Diary Entry"
                
                # Clean title: remove quotes, "Diary Session:" prefix, etc.
                title = title.strip().strip('"').strip()
                if title.lower().startswith("diary session") or not title:
                    title = "Diary Entry"
                    
                # Get summary: use first paragraph or truncated text
                summary_text = lines[1] if len(lines) > 1 else clean_text
                # Remove the transcript portion 
                if "---" in summary_text:
                    summary_text = summary_text.split("---")[0]
                summary_text = summary_text.strip()[:200]
                
                # Format date nicely
                date_str = entry.created_at.strftime("%B %d, %Y") if entry.created_at else "Unknown"
                
                summaries.append(DiaryEntrySummary(
                    id=entry.id,
                    date=date_str,
                    title=title if title else "Diary Entry",
                    summary=summary_text if summary_text else "A diary entry."
                ))
            
            return summaries
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error fetching diary entries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch entries: {e}")

class DiaryEntryFull(BaseModel):
    id: str
    date: str
    title: str
    summary: str
    transcript: List[Dict[str, str]]

@app.get("/diary/entries/{entry_id}", response_model=DiaryEntryFull)
def get_diary_entry(entry_id: str):
    """
    Fetches a single diary entry with its full transcript for read-only view.
    """
    require_orchestrator()
    
    try:
        from api.database import SessionLocal
        from api.models import Entry
        import re
        
        def sanitize_think_tags(text: str) -> str:
            return re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE).strip()
        
        db = SessionLocal()
        try:
            entry = db.query(Entry).filter(Entry.id == entry_id).first()
            
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")
            
            clean_text = sanitize_think_tags(entry.text)
            
            # Parse transcript from stored format
            # Format: "Summary\n\n---\n[Full Transcript]\nrole: content\nrole: content"
            transcript = []
            if "---" in clean_text and "[Full Transcript]" in clean_text:
                transcript_section = clean_text.split("[Full Transcript]")[-1].strip()
                for line in transcript_section.split('\n'):
                    line = line.strip()
                    if line.startswith("user:"):
                        transcript.append({"role": "user", "content": line[5:].strip()})
                    elif line.startswith("assistant:"):
                        transcript.append({"role": "assistant", "content": line[10:].strip()})
            
            # Extract title and summary
            lines = clean_text.split('\n', 1)
            title = lines[0][:50] if lines else "Diary Entry"
            title = title.strip().strip('"').strip()
            if title.lower().startswith("diary session") or not title:
                title = "Diary Entry"
            
            summary_text = lines[1].split("---")[0].strip()[:200] if len(lines) > 1 and "---" in lines[1] else ""
            
            date_str = entry.created_at.strftime("%B %d, %Y") if entry.created_at else "Unknown"
            
            return DiaryEntryFull(
                id=entry.id,
                date=date_str,
                title=title if title else "Diary Entry",
                summary=summary_text if summary_text else "A diary entry.",
                transcript=transcript
            )
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching diary entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch entry: {e}")

@app.post("/diary/save")
def save_diary(req: DiarySaveRequest):
    """
    Finalizes a chat session: Summarizes, Persists, and Embeds.
    """
    orch = require_orchestrator()
    if not req.transcript:
         raise HTTPException(status_code=400, detail="Transcript empty")
         
    try:
        entry_id = orch.save_diary_session(req.transcript)
        return {"id": entry_id, "message": "Diary saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # Clean run
    uvicorn.run(app, host="127.0.0.1", port=8000)
