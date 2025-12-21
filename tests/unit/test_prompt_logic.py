from orchestrator.daily_questions import DailyQuestionGenerator
from orchestrator.engine import Orchestrator
from settings.manager import SettingsManager

def test_daily_prompt_contains_profile():
    """Verify built system prompt contains the user profile."""
    gen = DailyQuestionGenerator()
    profile = "User likes climbing."
    
    prompt = gen.build_system_prompt(profile)
    
    assert "[USER PROFILE]" in prompt
    assert "User likes climbing." in prompt

def test_orchestrator_injects_safety_and_profile(mock_settings):
    """Verify Orchestrator.generate_reflection prompt construction (white-box logic check)."""
    # This is harder to test without exposing the prompt builder or mocking Ollama to capture the call.
    # We will check the method logic by mocking Ollama.chat and inspecting arguments.
    from unittest.mock import MagicMock
    
    orch = Orchestrator(mock_settings)
    orch.user_profile = "PROFILE_SIGNAL"
    orch.safety.get_system_prompt_addendum = MagicMock(return_value=" SAFETY_BLOCK")
    orch.ollama.chat = MagicMock(return_value={"message": {"content": "ok"}})
    
    # Act
    orch.generate_reflection("context")
    
    # Assert
    args, kwargs = orch.ollama.chat.call_args
    messages = args[1] # 0 is model, 1 is messages
    sys_content = messages[0]["content"]
    
    assert "[PERSONALIZATION]" in sys_content
    assert "PROFILE_SIGNAL" in sys_content
    assert "SAFETY_BLOCK" in sys_content
