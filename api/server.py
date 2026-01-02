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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
    qdrant_url: str
    stt_path: str
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

# --- Endpoints ---

@app.get("/setup/status")
def get_setup_status():
    """Returns whether the backend is configured."""
    return {
        "is_configured": settings_mgr.exists(),
        "config_path": str(settings_mgr.config_path)
    }

@app.post("/setup/complete")
def complete_setup(req: SetupRequest):
    """
    Saves the configuration and user profile.
    This replaces the CLI setup_wizard.py flow.
    """
    from settings.config_model import AppConfig, OllamaConfig, QdrantConfig, STTConfig
    
    # 1. Save Config
    config = AppConfig(
        ollama=OllamaConfig(
            base_url=req.ollama_url,
            chat_model=req.chat_model,
            embed_model=req.embed_model
        ),
        qdrant=QdrantConfig(
            url=req.qdrant_url
        ),
        stt=STTConfig(
            model_path=req.stt_path
        )
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
        
        # Use orchestrator's Ollama connection for generation
        response = orch.ollama.generate(prompt)
        
        # Also save this as a diary entry
        orch.process_new_entry(
            text=req.message,
            feature_type="open_diary",
            tags=["diary", "chat"]
        )
        
        return {"response": response}
    except Exception as e:
        print(f"Chat error: {e}")
        # Return a fallback response instead of failing completely
        return {
            "response": "I'm here to listen. Could you tell me more about what's on your mind?"
        }


if __name__ == "__main__":
    import uvicorn
    # Clean run
    uvicorn.run(app, host="127.0.0.1", port=8000)
