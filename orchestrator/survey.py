from typing import List, Dict, Any
from pydantic import BaseModel

class SurveyQuestion(BaseModel):
    id: str
    text: str
    dimension: str
    reverse: bool = False

class SurveyManager:
    """
    Manages the Onboarding Survey (Big Five / OCEAN style).
    Generates non-clinical 'Interaction Style' signals.
    """
    
    # 10-Item Short Form (TIPI-inspired structure, rephrased for simplicity)
    QUESTIONS = [
        # Openness
        SurveyQuestion(id="o1", text="I see myself as open to new experiences.", dimension="Openness"),
        SurveyQuestion(id="o2_r", text="I see myself as conventional/traditional.", dimension="Openness", reverse=True),
        # Conscientiousness
        SurveyQuestion(id="c1", text="I see myself as self-disciplined and organized.", dimension="Conscientiousness"),
        SurveyQuestion(id="c2_r", text="I see myself as disorganized or careless.", dimension="Conscientiousness", reverse=True),
        # Extraversion
        SurveyQuestion(id="e1", text="I see myself as extraverted, enthusiastic.", dimension="Extraversion"),
        SurveyQuestion(id="e2_r", text="I see myself as reserved, quiet.", dimension="Extraversion", reverse=True),
        # Agreeableness
        SurveyQuestion(id="a1", text="I see myself as sympathetic, warm.", dimension="Agreeableness"),
        SurveyQuestion(id="a2_r", text="I see myself as critical, quarrelsome.", dimension="Agreeableness", reverse=True),
        # Neuroticism (Emotional Stability)
        SurveyQuestion(id="n1", text="I see myself as anxious, easily upset.", dimension="Neuroticism"),
        SurveyQuestion(id="n2_r", text="I see myself as calm, emotionally stable.", dimension="Neuroticism", reverse=True),
    ]

    def get_questions(self) -> List[Dict[str, Any]]:
        return [q.model_dump() for q in self.QUESTIONS]

    def compute_profile_text(self, answers: Dict[str, int]) -> str:
        """
        Input: Dict of {question_id: score_1_to_7}
        Output: A prompt-ready string description of preferences.
        """
        scores = {d: 0 for d in ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]}
        counts = {d: 0 for d in scores}
        
        # Mapping
        q_map = {q.id: q for q in self.QUESTIONS}
        
        for q_id, score in answers.items():
            if q_id not in q_map:
                continue
            
            q = q_map[q_id]
            # Normalize score 1-7 (assuming 7 point likert)
            val = score
            if q.reverse:
                val = 8 - score # Reverse: 1->7, 7->1
            
            scores[q.dimension] += val
            counts[q.dimension] += 1
            
        # Generate Text Signals
        signals = []
        
        # Openness
        avg_o = scores["Openness"] / max(1, counts["Openness"])
        if avg_o > 5.5: signals.append("User likely enjoys exploring new, abstract ideas.")
        elif avg_o < 3.5: signals.append("User likely prefers practical, familiar topics.")
        else: signals.append("User balances novelty with tradition.")

        # Conscientiousness
        avg_c = scores["Conscientiousness"] / max(1, counts["Conscientiousness"])
        if avg_c > 5.5: signals.append("Preferred style: Structured, goal-oriented interactions.")
        elif avg_c < 3.5: signals.append("Preferred style: Flexible, spontaneous flow.")
        
        # Extraversion
        avg_e = scores["Extraversion"] / max(1, counts["Extraversion"])
        if avg_e > 5.5: signals.append("Tone: Energetic and social.")
        elif avg_e < 3.5: signals.append("Tone: Calm and reflective.")
        
        # Agreeableness
        avg_a = scores["Agreeableness"] / max(1, counts["Agreeableness"])
        if avg_a > 5.5: signals.append("User values harmony and empathy highly.")
        elif avg_a < 3.5: signals.append("User appreciates directness and debate.")
        
        # Neuroticism
        avg_n = scores["Neuroticism"] / max(1, counts["Neuroticism"])
        if avg_n > 5.5: signals.append("Be extra gentle and supportive; avoid pressure.")
        elif avg_n < 3.5: signals.append("User is resilient; open to challenging questions.")
        
        return "\n".join(signals)
