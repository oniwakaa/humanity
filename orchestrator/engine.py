from typing import Dict, Any, List
from settings.manager import SettingsManager
from connectors.ollama import OllamaClient
from storage.journal import JournalStorage
from storage.memory import MemoryLayer
from utils.safety import SafetyGuardrails
from orchestrator.queues import JobQueue

from utils.audio_session import AudioSession
from stt.engine import STTEngine
from orchestrator.survey import SurveyManager

class Orchestrator:
    def __init__(self, settings_manager: SettingsManager):
        self.settings = settings_manager.get_config()
        self.journal = JournalStorage(self.settings.storage_path)
        self.memory = MemoryLayer(
            self.settings.qdrant.url, 
            self.settings.qdrant.collection_name
        )
        self.ollama = OllamaClient(self.settings.ollama.base_url)
        self.safety = SafetyGuardrails()
        self.survey_manager = SurveyManager()
        
        self.embed_queue = JobQueue(f"{self.settings.storage_path}/embed_jobs.jsonl")
        self.gen_queue = JobQueue(f"{self.settings.storage_path}/gen_jobs.jsonl")
        
        # Load User Profile
        self.user_profile = self._load_user_profile()

        # Audio Session State
        self.stt_engine = STTEngine(self.settings.stt.model_path)
        try:
            self.stt_engine.load_model()
        except Exception as e:
            print(f"Failed to load STT model: {e}")
            
        self.current_session: Optional[AudioSession] = None
        self.latest_transcript = ""

    def _load_user_profile(self) -> str:
        """Scans journal for latest survey entry."""
        # Inefficient for large journals, but fine for MVP MVP with small data.
        # Ideally, we query an index. 
        # Since we don't have a fast index for 'feature_type' in FileStorage yet,
        # we can just assume it's rare or check a cached file.
        # For true MVP: Iterate all entries.
        entries = self.journal.get_entries(limit=1000) # Check last 1000
        for e in entries:
            if e.get("feature_type") == "survey":
                # Found one. Compute profile.
                # Assuming 'text' field contains JSON string of answers or we look at payload?
                # The prompt said "Persist raw answers".
                # Let's assume the 'chunks' or structure holds it, or we stored it in 'text' as a JSON blob.
                # Or better, we store the *computed* profile in a new field if possible, 
                # but 'text' is the canonical content.
                # Let's assume 'text' is the Computed Profile Text for simplicity of reading,
                # and raw answers are in `tags` or a specific metadata field we haven't implemented yet.
                # Actually, prompts said "Persist raw answers".
                # Let's assume the entry `text` is the JSON of answers.
                try:
                    import json
                    answers = json.loads(e["text"])
                    return self.survey_manager.compute_profile_text(answers)
                except:
                    pass
        
        return "Interaction Style: Neutral. New user."

    def start_recording_session(self):
        """Starts a 'Your Story' voice session."""
        if self.current_session and self.current_session.active:
            raise ValueError("Session already active")
            
        def on_transcript(text):
            self.latest_transcript = text
            # In a real app, we'd push this via Websocket to UI
            
        self.current_session = AudioSession(self.stt_engine, on_transcript)
        self.current_session.start()
    
    def stop_recording_session(self) -> str:
        """Stops session and returns final text."""
        if not self.current_session:
            raise ValueError("No active session")
            
        self.current_session.stop()
        self.current_session = None
        
        # Return the accumulated text
        # Note: process_stream returns "current partial".
        # If the window rolled over, we lost data. 
        # fixing that requires STTEngine to commit segments.
        # For MVP, we presume `latest_transcript` is the best we have.
        return self.latest_transcript

    def process_new_entry(self, text: str, feature_type: str, tags: List[str] = None):
        """
        Main entry point for saving content.
        1. Access Journal Storage -> Write
        2. Create Embedding Job -> Queue
        """
        # 1. Save to Journal
        entry_id = self.journal.add_entry(text, feature_type, tags)
        
        # 2. Queue for Embedding
        if feature_type != "no_memory": # Check consent
            self.embed_queue.push({
                "type": "embed",
                "entry_id": entry_id,
                "text": text,
                "timestamp": 0 # TODO: use real TS
            })
            
        return entry_id

    def run_embedding_worker(self):
        """
        Processes one item from the embedding queue.
        Should be called periodically or by a background thread.
        """
        job = self.embed_queue.peek()
        if not job:
            return
            
        try:
            # 1. Generate Embedding
            vec = self.ollama.embed(self.settings.ollama.embed_model, job["text"])
            
            # 2. Upsert to Qdrant
            # Need to chunk properly in real impl
            chunks = [{
                "entry_id": job["entry_id"],
                "text": job["text"],
                "chunk_id": f"{job['entry_id']}_0"
            }]
            self.memory.upsert_chunks(chunks, [vec])
            
            # 3. Remove from queue
            self.embed_queue.pop()
            
        except Exception as e:
            print(f"Embedding failed: {e}")
            # Retry logic needed here (exponential backoff)

    def generate_reflection(self, context_query: str) -> str:
        """Generates a reflection based on context."""
        # 1. Search Memory
        try:
             query_vec = self.ollama.embed(self.settings.ollama.embed_model, context_query)
             hits = self.memory.search(query_vec, limit=3)
             
             context_text = "\n".join([h.get("text", "") for h in hits])
        except Exception as e:
             print(f"RAG Retrieval failed: {e}")
             context_text = ""
        
        # 2. Form Prompt
        system_prompt = (
            "You are a helpful, empathetic AI journaling assistant. "
            "Your goal is to help the user reflect on their thoughts. "
            f"\n[PERSONALIZATION]\n{self.user_profile}\n"
            f"{self.safety.get_system_prompt_addendum()}"
        )
        
        user_prompt = f"Relevant past memories:\n{context_text}\n\nCurrent thought or topic: {context_query}\n\nSuggest a deep, non-judgmental follow-up question."
        
        if not self.safety.check_prompt(user_prompt):
            return "I can't provide a reflection on this topic due to safety guidelines."
            
        # 3. Call LLM
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = self.ollama.chat(
                self.settings.ollama.chat_model, 
                messages,
                options={"num_ctx": self.settings.ollama.num_ctx}
            )
            content = response.get("message", {}).get("content", "")
            return self.safety.sanitize_response(content)
        except Exception as e:
            print(f"Generation failed: {e}")
            return "I'm having trouble thinking of a reflection right now. Please tell me more."

    def generate_daily_questions(self) -> Dict[str, Any]:
        """Orchestreates generation of daily questions."""
        from orchestrator.daily_questions import DailyQuestionGenerator
        from datetime import datetime
        from uuid import uuid4
        
        generator = DailyQuestionGenerator()
        cycle_id = str(uuid4())
        
        # 1. Retrieve Context (Naive RAG: Random recent chunks)
        # In real impl, we specific query filters for 'your_story' or 'journal'
        context_text = ""
        try:
            # We assume embedding of "Current life themes" or similar generic query
            query_vec = self.ollama.embed(self.settings.ollama.embed_model, "Meaningful recent events and feelings")
            hits = self.memory.search(query_vec, limit=5)
            context_text = "\n".join([h.get("text", "") for h in hits])
        except:
             pass

        # 2. Call LLM
        questions = generator.STATIC_FALLBACK
        try:
            sys_prompt = generator.build_system_prompt(self.user_profile)
            user_prompt = generator.build_user_prompt(context_text)
            
            resp = self.ollama.chat(self.settings.ollama.chat_model, [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ], options={"num_ctx": self.settings.ollama.num_ctx})
            content = resp.get("message", {}).get("content", "")
            questions = generator.parse_response(content)
        except Exception as e:
            print(f"Daily Gen Failed: {e}")
            
        # 3. Persist Set
        payload = {
            "cycle_id": cycle_id,
            "date": datetime.now().isoformat(),
            "questions": questions
        }
        
        import json
        self.process_new_entry(
            text=json.dumps(payload),
            feature_type="daily_questions_set",
            tags=["daily_generated"]
        )
        
        return payload

    def submit_daily_answers(self, cycle_id: str, answers: List[Dict[str, Any]]):
        """
        answers: [{"question_id": "...", "answer": "..."}]
        """
        import json
        payload = {
            "cycle_id": cycle_id,
            "answers": answers
        }
        
        # Save
        entry_id = self.process_new_entry(
            text=json.dumps(payload),
            feature_type="daily_questions_answ", # Truncated to avoid long tag issues if any
            tags=["daily_answer"]
        )
        return entry_id
