from typing import List

class SafetyGuardrails:
    def __init__(self):
        self.clinical_terms = [
            "diagnose", "depression", "anxiety disorder", "therapy", "treatment", 
            "prescription", "symptom", "cure"
        ]
        self.diagnostic_phrases = [
            "you have", "sounds like", "suffering from"
        ]

    def check_prompt(self, prompt: str) -> bool:
        """Checks if a prompt is safe to send. Returns True if safe."""
        # Simple keyword check for MVP
        prompt_lower = prompt.lower()
        if any(term in prompt_lower for term in self.clinical_terms):
            return False
        return True

    def sanitize_response(self, text: str) -> str:
        """Sanitizes AI response to ensure non-diagnostic language."""
        # Replace definitive statements with hedging
        text = text.replace("You are", "You might be")
        text = text.replace("You have", "It seems you have")
        
        # In a real impl, this would be a more robust NLP check or an LLM call
        # to a smaller model to 'rewrite' if needed, or just strict instructing.
        return text

    def get_system_prompt_addendum(self) -> str:
        return (
            "\n[SAFETY RULES]\n"
            "1. Do NOT diagnose or offer medical advice.\n"
            "2. Use hedging language (may, might, could).\n"
            "3. Remind the user they have agency ('If you want', 'Optional').\n"
        )
