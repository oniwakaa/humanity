import json
import random
from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4

class DailyQuestionGenerator:
    """
    Generates personalized daily reflection questions using a Hybrid Model:
    - Core Static Set (Fixed)
    - Dynamic LLM Set (generated from Context)
    """
    
    # 1. The Fixed Core (Static)
    CORE_QUESTIONS = [
        {
            "id": "core_mood",
            "type": "likert",
            "text": "How are you feeling overall today?",
            "lowLabel": "Very Low",
            "highLabel": "Wonderful"
        },
        {
            "id": "core_presence",
            "type": "likert",
            "text": "How present were you in your actions?",
            "lowLabel": "Distracted", 
            "highLabel": "Fully Present"
        },
        {
            "id": "core_gratitude",
            "type": "open",
            "text": "What is one thing you are grateful for right now?"
        }
    ]

    def build_system_prompt(self, user_profile: str, user_context: str = "", recent_themes: str = "") -> str:
        return (
            "You are a thoughtful AI companion helping users reflect deeply on their lives.\n"
            f"[USER PROFILE]\n{user_profile}\n"
            f"[RECENT CONTEXT]\n{user_context}\n"
            f"[RECURRING THEMES]\n{recent_themes}\n"
            "Your goal is to help the user grow by asking probing, insightful questions based on their recent life events.\n"
            "Start with broad questions and narrow based on user responses.\n"
            "Reference past entries when relevant (e.g., 'Last week you mentioned...').\n"
            "Ask 'why' and 'how' more than 'what' to explore emotions.\n"
            "Follow emotional threads (e.g., if the user mentions stress or joy, explore that).\n"
            "You must generate 5-7 *new* questions to complement the standard daily check-in.\n"
            "Output must be strictly valid JSON containing an array of questions."
        )

    def build_user_prompt(self, context_text: str) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return (
            f"Date: {date_str}\n"
            f"User's Recent Context (Story/Diary/Reflections):\n{context_text}\n\n"
            "Based on the struggles, wins, or themes in the context above, generate 7 personalized reflection questions.\n"
            "Use a mix of:\n"
            "- 'likert' (Scale 1-7)\n"
            "- 'open' (Open-ended for deep thought)\n"
            "Ask 'why' and 'how' more than 'what' to explore emotions.\n"
            "Reference past entries when relevant (e.g., 'Last week you mentioned...').\n"
            "Follow emotional threads (e.g., if the user mentions stress or joy, explore that).\n\n"
            "OUTPUT FORMAT (JSON ONLY). FIELDS MUST MATCH:\n"
            "- id: string\n"
            "- type: 'likert' | 'open'\n"
            "- text: string (The question content)\n"
            "- lowLabel: string (For likert only, e.g. 'Not at all')\n"
            "- highLabel: string (For likert only, e.g. 'Completely')\n\n"
            "EXAMPLE:\n"
            "{\n"
            '  "questions": [\n'
            '    {"type": "open", "text": "You mentioned anxiety. How did that manifest?"},\n'
            '    {"type": "likert", "text": "I felt in control of...", "lowLabel": "Low", "highLabel": "High"}\n'
            '  ]\n'
            "}"
        )

    def combine_questions(self, dynamic_questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merges Core Static questions with Dynamic ones."""
        # 1. Start with Core
        final_set = list(self.CORE_QUESTIONS)
        
        # 2. Add Valid Dynamic Questions
        for q in dynamic_questions:
            # Basic validation
            if "text" in q and "type" in q:
                # Assign ID if missing
                if "id" not in q:
                    q["id"] = f"dyn_{str(uuid4())[:8]}"
                final_set.append(q)
                
        # 3. Cap at 10 total
        return final_set[:10]

    def parse_response(self, split_text: str) -> List[Dict[str, Any]]:
        """Parses LLM output into dynamic questions list."""
        try:
            clean_text = split_text.strip()
            # Heuristic cleaning for markdown code blocks
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(clean_text)
            return data.get("questions", [])
            
        except Exception as e:
            print(f"JSON Parsing failed during Question Gen: {e}")
            return [] # Return empty so we just get Core questions
