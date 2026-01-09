from typing import Dict, Any, List, Optional
import re

from settings.manager import SettingsManager
from connectors.ollama import OllamaClient
from storage.db_manager import DBManager
from storage.memory import MemoryLayer
from utils.safety import SafetyGuardrails
from orchestrator.queues import JobQueue
from orchestrator.survey import SurveyManager


def smart_truncate(text: str, max_length: int, prefer_sentence: bool = True) -> str:
    """
    Truncate text intelligently at sentence or word boundaries.
    
    Args:
        text: Text to truncate
        max_length: Maximum character length
        prefer_sentence: If True, prefer sentence endings (.!?) over word endings
        
    Returns:
        Truncated text with "..." if truncated, original text if within limit
    """
    if not text or len(text) <= max_length:
        return text.strip()
    
    # Try to find a sentence boundary first
    if prefer_sentence:
        # Find the last sentence-ending punctuation before max_length
        sentence_end = max(
            text.rfind('.', 0, max_length),
            text.rfind('!', 0, max_length),
            text.rfind('?', 0, max_length)
        )
        if sentence_end > max_length * 0.5:  # Only use if we get at least 50% of content
            return text[:sentence_end + 1].strip()
    
    # Fall back to word boundary
    last_space = text.rfind(' ', 0, max_length)
    if last_space > max_length * 0.7:  # Only truncate at word if we get 70%+
        return text[:last_space].strip() + "..."
    
    # Last resort: hard truncate
    return text[:max_length - 3].strip() + "..."


def parse_summary_response(raw_response: str) -> Dict[str, str]:
    """
    Parse the LLM response to extract title and summary.
    
    Handles:
    - Case-insensitive label detection (Title:, title:, TITLE:, etc.)
    - Missing labels with graceful fallbacks
    - Smart truncation to fit UI constraints
    
    Args:
        raw_response: Raw response from LLM
        
    Returns:
        Dict with 'title' and 'summary' keys
    """
    result = {
        "title": "Diary Entry",
        "summary": "A reflective diary entry."
    }
    
    if not raw_response:
        return result
    
    # Normalize: strip but preserve internal structure
    text = raw_response.strip()
    
    # Try case-insensitive label extraction
    title_match = None
    summary_match = None
    
    # Look for title (case-insensitive)
    title_pattern = re.compile(r'^title:\s*(.+)$', re.MULTILINE | re.IGNORECASE)
    title_matches = title_pattern.findall(text)
    if title_matches:
        # Get the title from the first match
        title_match = title_matches[0].strip()
        # Remove any trailing labels or content
        if "\n" in title_match:
            title_match = title_match.split("\n")[0].strip()
        # Remove "Summary:" suffix if present
        title_match = re.split(r'\s+summary:', title_match, flags=re.IGNORECASE)[0].strip()
    
    # Look for summary (case-insensitive)
    summary_pattern = re.compile(r'summary:\s*(.+)$', re.IGNORECASE)
    summary_match = summary_pattern.search(text)
    if summary_match:
        summary_match = summary_match.group(1).strip()
    
    # Fallback: if no labels found, try line-based parsing
    if not title_match or not summary_match:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) >= 2:
            # Assume first non-empty line is title, rest is summary
            if not title_match:
                title_match = lines[0]
            if not summary_match:
                summary_match = ' '.join(lines[1:])
        elif len(lines) == 1:
            # Single line: use as title, auto-generate summary
            if not title_match:
                title_match = lines[0]
            # summary stays as default
    
    # Apply smart truncation
    if title_match:
        # Title: max 60 chars, prefer sentence boundary first (though titles rarely have them)
        result["title"] = smart_truncate(title_match, 60, prefer_sentence=False)
    
    if summary_match:
        # Summary: max 130 chars (leaves room for "..." if needed)
        result["summary"] = smart_truncate(summary_match, 130, prefer_sentence=True)
    
    return result

class Orchestrator:
    def __init__(self, settings_manager: SettingsManager):
        print("[STATUS] 6 || Reading Settings...", flush=True)
        self.settings = settings_manager.get_config()
        self.journal = DBManager() # Replaces JournalStorage(path)
        
        print("[STATUS] 8 || Connecting to Memory Core...", flush=True)
        self.memory = MemoryLayer(
            persistence_path=f"{self.settings.storage_path}/chroma",
            collection_name="journal_entries"
        )
        
        print(f"[STATUS] 12 || Initializing Ollama Bridge ({self.settings.ollama.base_url})...", flush=True)
        self.ollama = OllamaClient(self.settings.ollama.base_url)
        self.safety = SafetyGuardrails()
        self.survey_manager = SurveyManager()
        
        self.embed_queue = JobQueue(f"{self.settings.storage_path}/embed_jobs.jsonl")
        self.gen_queue = JobQueue(f"{self.settings.storage_path}/gen_jobs.jsonl")

        # Load User Profile
        print("[STATUS] 18 || Loading User Profile...", flush=True)
        self.user_profile = self._load_user_profile()

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
            # 2. Upsert to Qdrant
            import uuid
            from utils.text_processing import chunk_text
            
            text_chunks = chunk_text(job["text"])
            chunks_to_upsert = []
            vectors_to_upsert = []
            
            for i, chunk in enumerate(text_chunks):
                # Embed each chunk
                vec = self.ollama.embed(self.settings.ollama.embed_model, chunk)
                
                chunk_id = str(uuid.uuid5(uuid.UUID(job['entry_id']), str(i)))
                
                chunks_to_upsert.append({
                    "entry_id": job["entry_id"],
                    "text": chunk,
                    "chunk_index": i,
                    "chunk_id": chunk_id
                })
                vectors_to_upsert.append(vec)

            if chunks_to_upsert:
                self.memory.upsert_chunks(chunks_to_upsert, vectors_to_upsert)
            
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
        """Orchestrates generation of daily questions."""
        from orchestrator.daily_questions import DailyQuestionGenerator
        from datetime import datetime
        from uuid import uuid4
        
        # 0. Check for existing Cycle for today (Latency/Caching Strategy)
        # Note: In a real app we query DB. For now, we generate fresh or check last entry if we had that logic.
        # But prompt asked for "Propose... or implement". 
        # We will implement "Generate Fresh" but efficiently.
        
        generator = DailyQuestionGenerator()
        cycle_id = str(uuid4())
        
        # 1. Retrieve Context (Hybrid Input)
        context_text = ""
        try:
            # Query vector store for recent themes
            query_vec = self.ollama.embed(self.settings.ollama.embed_model, "Recent thoughts patterns feelings events")
            hits = self.memory.search(query_vec, limit=5)
            context_text = "\n".join([f"- {h.get('text', '')}" for h in hits])
        except Exception as e:
             print(f"Context retrieval failed: {e}")

        # 2. Call LLM (Dynamic Part)
        dynamic_questions = []
        try:
            sys_prompt = generator.build_system_prompt(self.user_profile)
            user_prompt = generator.build_user_prompt(context_text)
            
            resp = self.ollama.chat(self.settings.ollama.chat_model, [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ], options={"num_ctx": self.settings.ollama.num_ctx})
            
            content = resp.get("message", {}).get("content", "")
            dynamic_questions = generator.parse_response(content)
        except Exception as e:
            print(f"Daily Gen LLM Failed: {e}")
            
        # 3. Merge (Hybrid Output)
        final_questions = generator.combine_questions(dynamic_questions)
            
        # 4. Persist Set
        payload = {
            "cycle_id": cycle_id,
            "date": datetime.now().isoformat(),
            "questions": final_questions
        }
        
        # Save to DB via new Manager
        # We store as a special entry type or better, use the DailyCycle model if we updated manager to support it.
        # Current DBManager only supports Entry.
        # Let's save as Entry feature_type="daily_questions_set" for MVP compatibility
        import json
        self.process_new_entry(
            text=json.dumps(payload),
            feature_type="daily_questions_set",
            tags=["daily_generated"]
        )
        
        return payload

        return entry_id
    
    def chat_session(self, message: str, context_history: List[Dict[str, str]]) -> str:
        """
        Processes a chat message with RAG context from past diary entries.
        """
        # 1. RAG Retrieval (Focus on 'now', but use 'past' for depth)
        try:
            query_vec = self.ollama.embed(self.settings.ollama.embed_model, message)
            # Filter for diary/journal entries only if possible, but 'open_diary' is the type.
            hits = self.memory.search(query_vec, limit=3, filters={"feature_type": "open_diary"})
            rag_context = "\n".join([f"- {h.get('text', '')}" for h in hits])
        except Exception as e:
            print(f"Chat RAG Failed: {e}")
            rag_context = ""
            
        # 2. Construct System Prompt
        system_prompt = (
            "You are an empathetic, reflective diary companion. "
            "Your goal is to help the user explore their current thoughts deeper.\n"
            "INSTRUCTIONS:\n"
            "- Use the provided [PAST DIARY CONTEXT] to spot patterns if relevant, but...\n"
            "- PRIORITIZE the user's [CURRENT INPUT] and emotion.\n"
            "- Do not be purely retrospective. Focus on the 'now'.\n"
            "- Keep responses concise (2-3 sentences), warm, and non-judgmental.\n\n"
            f"[PAST DIARY CONTEXT]:\n{rag_context}\n\n"
            f"[USER PROFILE]:\n{self.user_profile}"
        )
        
        # 3. Call LLM
        messages = [{"role": "system", "content": system_prompt}]
        # Add history
        for msg in context_history[-5:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        
        # Add current
        messages.append({"role": "user", "content": message})
        
        try:
            resp = self.ollama.chat(
                self.settings.ollama.chat_model, 
                messages, 
                options={"num_ctx": self.settings.ollama.num_ctx}
            )
            return resp.get("message", {}).get("content", "")
        except Exception as e:
            print(f"Chat Gen failed: {e}")
            return "I'm listening. Please go on."

    def save_diary_session(self, full_transcript: List[Dict[str, str]]) -> str:
        """
        Summarizes and saves a completed diary chat session.
        Generates a concise title and summary for the diary book UI.
        """
        # 1. Generate Title and Summary
        combined_text = "\n".join([f"{m['role']}: {m['content']}" for m in full_transcript])
        
        title = "Diary Entry"
        summary = "A reflective diary entry."
        
        try:
            prompt = (
                "Based ONLY on the following diary conversation, create a very brief title and summary.\n\n"
                "TITLE: A concise title in 6-8 words (no quotes, no labels).\n"
                "SUMMARY: A summary in exactly 25-30 words that captures the main themes and emotions discussed.\n"
                "Write in first person as the user. Do NOT add any information not present in the conversation.\n\n"
                f"CONVERSATION:\n{combined_text}\n\n"
                "Format exactly as:\nTitle: <title>\nSummary: <summary>"
            )
            resp = self.ollama.chat(
                self.settings.ollama.chat_model,
                [{"role": "user", "content": prompt}],
                options={"num_ctx": 2048, "num_predict": 100}  # Strict token limit
            )
            content = resp.get("message", {}).get("content", "")
            
            # Parse the response with robust label extraction
            parsed = parse_summary_response(content)
            title = parsed["title"]
            summary = parsed["summary"]
                
        except Exception as e:
            print(f"Summary Gen Failed: {e}")
            
        # 2. Persist
        # We save the title + summary as the main content for searching, and the transcript after
        final_content = f"{title}\n\n{summary}\n\n---\n[Full Transcript]\n{combined_text}"
        
        entry_id = self.process_new_entry(
            text=final_content,
            feature_type="open_diary", # This ensures it's found in RAG
            tags=["diary", "session"]
        )
        return entry_id
