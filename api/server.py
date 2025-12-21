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
# Ensure default data path for MVP if not set
if not settings_mgr.exists():
    # Fallback or error? For MVP we assume setup_wizard ran.
    # But if not, we can load defaults.
    try:
        config = settings_mgr.load_settings()
    except:
        # Use defaults if setup skipped for dev?
        # Better to fail fast as per "setup_wizard has been executed" context.
        pass

orchestrator = Orchestrator(settings_mgr)
worker = BackgroundWorker(orchestrator)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task = asyncio.create_task(worker.run())
    yield
    # Shutdown
    worker.stop()
    await task

app = FastAPI(title="Humanity API", lifespan=lifespan)

# --- Models ---
class EntryCreate(BaseModel):
    text: str
    tags: Optional[List[str]] = []

class EntryResponse(BaseModel):
    id: str
    message: str

class ReflectionRequest(BaseModel):
    entry_id: str


# --- Endpoints ---

@app.get("/health")
def health_check():
    ollama_status = "ok" if orchestrator.ollama.check_health() else "error"
    qdrant_status = "ok" if orchestrator.memory.check_health() else "error"
    return {"status": "ok", "ollama": ollama_status, "qdrant": qdrant_status}

@app.post("/entry", response_model=EntryResponse, status_code=201)
def create_entry(entry: EntryCreate):
    """
    Creates a new Free Diary entry.
    """
    if not entry.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
        
    try:
        # feature_type="free_diary"
        entry_id = orchestrator.process_new_entry(
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
    try:
        ollama_ok = orchestrator.ollama.check_health()
        # Qdrant check not implemented in orchestrator yet exposed, but we can try basic
        return {
            "ollama_reachable": ollama_ok,
            "qdrant_configured": orchestrator.memory.check_health()
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/story/start")
def start_story_session():
    try:
        orchestrator.start_recording_session()
        return {"status": "started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start recording: {e}")

@app.post("/story/stop", response_model=EntryResponse)
def stop_story_session():
    try:
        text = orchestrator.stop_recording_session()
        if not text.strip():
             return EntryResponse(id="none", message="No text transcribed.")
             
        entry_id = orchestrator.process_new_entry(
            text=text, 
            feature_type="your_story",
            tags=["voice", "your_story"]
        )
        return EntryResponse(id=entry_id, message="Story saved.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing story: {e}")

class ReflectionRequest(BaseModel):
    entry_id: str

@app.post("/story/reflect")
def reflect_on_story(req: ReflectionRequest):
    """
    Triggers RAG-based reflection on a specific entry.
    """
    entry = orchestrator.journal.get_entry(req.entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
        
    # Generate reflection based on the text of the entry
    suggestion = orchestrator.generate_reflection(entry["text"])
    return {"suggestion": suggestion}

@app.get("/survey/questions")
def get_survey_questions():
    return orchestrator.survey_manager.get_questions()

@app.get("/survey/status")
def get_survey_status():
    # Check if profile is default
    is_completed = orchestrator.user_profile != "Interaction Style: Neutral. New user."
    return {"completed": is_completed}

@app.post("/survey/submit")
def submit_survey(answers: Dict[str, int]):
    """
    Submits survey answers.
    Expects {q_id: score} mapping.
    """
    import json
    
    # Validation could happen here (range 1-7)
    
    # Save as journal entry
    # We store the raw answers JSON in 'text' as per plan assumption in Orchestrator._load_user_profile
    text_payload = json.dumps(answers)
    
    try:
        entry_id = orchestrator.process_new_entry(
            text=text_payload, 
            feature_type="survey",
            tags=["survey", "onboarding"]
        )
        
        # Force reload profile immediately (naive)
        orchestrator.user_profile = orchestrator._load_user_profile()
        
        return {"status": "saved", "entry_id": entry_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save survey: {e}")

@app.post("/daily/generate")
def generate_daily():
    try:
        data = orchestrator.generate_daily_questions()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DailySubmission(BaseModel):
    cycle_id: str
    answers: List[Dict[str, Any]]

@app.post("/daily/submit")
def submit_daily(sub: DailySubmission):
    try:
        entry_id = orchestrator.submit_daily_answers(sub.cycle_id, sub.answers)
        return {"status": "saved", "entry_id": entry_id}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Clean run
    uvicorn.run(app, host="127.0.0.1", port=8000)
