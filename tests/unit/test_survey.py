from orchestrator.survey import SurveyManager

def test_survey_scoring_logic():
    manager = SurveyManager()
    
    # Test High Openness
    # o1: I see myself as open to new experiences.
    # o2_r: I see myself as conventional/traditional.
    
    # Scenario: Very Open User
    # o1 = 7 (Strongly Agree)
    # o2_r = 1 (Strongly Disagree) -> Reverse 7
    
    answers = {
        "o1": 7,
        "o2_r": 1
    }
    
    text = manager.compute_profile_text(answers)
    assert "User likely enjoys exploring new, abstract ideas" in text

def test_survey_scoring_reverse_coding():
    manager = SurveyManager()
    
    # Scenario: Low Openness (Traditional)
    # o1 = 1
    # o2_r = 7 -> Reverse 1
    
    answers = {
        "o1": 1,
        "o2_r": 7
    }
    
    text = manager.compute_profile_text(answers)
    assert "User likely prefers practical, familiar topics" in text
