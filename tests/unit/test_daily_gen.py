import json
from orchestrator.daily_questions import DailyQuestionGenerator

def test_parse_response_valid_json():
    gen = DailyQuestionGenerator()
    
    json_text = """
    {
      "questions": [
        {"type": "mcq", "prompt": "Q1", "options": ["A", "B"]},
        {"type": "likert", "prompt": "Q2", "scale_min": 1, "scale_max": 5},
        {"type": "open", "prompt": "Q3"},
         {"type": "open", "prompt": "Q4"},
          {"type": "open", "prompt": "Q5"},
           {"type": "open", "prompt": "Q6"}
      ]
    }
    """
    
    questions = gen.parse_response(json_text)
    assert len(questions) == 6
    assert questions[0]["prompt"] == "Q1"

def test_parse_response_malformed_fallback():
    gen = DailyQuestionGenerator()
    
    bad_text = "I am not JSON"
    
    questions = gen.parse_response(bad_text)
    assert questions == gen.STATIC_FALLBACK
    assert len(questions) >= 6

def test_parse_response_markdown_strip():
    gen = DailyQuestionGenerator()
    
    md_text = """```json
    { "questions": [{"type":"open", "prompt":"real"}]}
    ```""" 
    # Note: Only 1 question provided, should trigger fallback append
    
    questions = gen.parse_response(md_text)
    assert len(questions) >= 6 
    # Should contain the real one + fallbacks
    assert questions[0]["prompt"] == "real"
