import json
import random
from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4

class DailyQuestionGenerator:
    """
    Generates personalized daily reflection questions.
    """
    
    # Fallback set if Ollama is down/fails
    STATIC_FALLBACK = [
        {"id": "fb1", "type": "mcq", "prompt": "How are you feeling today?", "options": ["Energized", "Calm", "Tired", "Anxious", "Neutral"]},
        {"id": "fb2", "type": "likert", "prompt": "I felt productive today.", "scale_min": 1, "scale_max": 5, "scale_labels": ["Strongly Disagree", "Strongly Agree"]},
        {"id": "fb3", "type": "open", "prompt": "What was the highlight of your day?"},
        {"id": "fb4", "type": "mcq", "prompt": "Who did you spend the most time with?", "options": ["Family", "Friends", "Colleagues", "Alone", "Strangers"]},
        {"id": "fb5", "type": "likert", "prompt": "I felt true to my values today.", "scale_min": 1, "scale_max": 5, "scale_labels": ["No", "Yes"]},
        {"id": "fb6", "type": "open", "prompt": "What is one thing you want to do differently tomorrow?"}
    ]

    def build_system_prompt(self, user_profile: str) -> str:
        return (
            "You are an expert AI coach specializing in deep, personalized reflection.\n"
            f"[USER PROFILE]\n{user_profile}\n"
            "Your task is to generate a set of 6-10 Daily Deep Questions for the user.\n"
            "Mix of: \n"
            "- MCQ (Multiple Choice)\n"
            "- Likert (Scale 1-5)\n"
            "- Open-Ended\n"
            "Output must be strictly valid JSON."
        )

    def build_user_prompt(self, context_text: str) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return (
            f"Date: {date_str}\n"
            f"Recent Context:\n{context_text}\n\n"
            "Generate a JSON object with this structure:\n"
            "{\n"
            '  "questions": [\n'
            '    {"type": "mcq", "prompt": "...", "options": ["A", "B", ...]}, \n'
            '    {"type": "likert", "prompt": "...", "scale_min": 1, "scale_max": 5, "scale_labels": ["Low", "High"]}, \n'
            '    {"type": "open", "prompt": "..."}\n'
            "  ]\n"
            "}\n"
            "Ensure questions are non-judgmental, challenging, and varied."
        )

    def parse_response(self, split_text: str) -> List[Dict[str, Any]]:
        """Parses LLM output into questions list."""
        try:
            # Cleanup potential markdown ticks
            clean_text = split_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            
            data = json.loads(clean_text)
            qs = data.get("questions", [])
            
            # Simple validation
            valid = []
            for q in qs:
                if "prompt" in q and "type" in q:
                    # add IDs if missing
                    q["id"] = q.get("id") or str(uuid4())[:8]
                    valid.append(q)
                    
            if len(valid) < 6:
                # If too few, append fallback to reach 6
                needed = 6 - len(valid)
                valid.extend(self.STATIC_FALLBACK[:needed])
                
            return valid[:10] # cap at 10
            
        except Exception as e:
            print(f"JSON Parsing failed: {e}")
            return self.STATIC_FALLBACK
