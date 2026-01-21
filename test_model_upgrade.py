#!/usr/bin/env python3
"""
Test script to verify the model upgrade and prompt updates.
"""

import sys
from settings.config_model import OllamaConfig
from orchestrator.daily_questions import DailyQuestionGenerator

def test_model_config():
    """Test that the model config is updated correctly."""
    config = OllamaConfig()
    print("Testing model configuration...")
    assert config.chat_model == "ministral:3b", f"Expected 'ministral:3b', got '{config.chat_model}'"
    assert config.num_ctx == 16384, f"Expected 16384, got {config.num_ctx}"
    print("✓ Model configuration is correct.")

def test_prompt_updates():
    """Test that the prompts are updated correctly."""
    generator = DailyQuestionGenerator()
    user_profile = "User likes climbing."
    user_context = "User mentioned feeling stressed about work."
    recent_themes = "stress, work, anxiety"
    
    print("\nTesting system prompt updates...")
    system_prompt = generator.build_system_prompt(user_profile, user_context, recent_themes)
    
    # Check for new additions
    assert "thoughtful AI companion" in system_prompt, "System prompt should include 'thoughtful AI companion'"
    assert "[RECENT CONTEXT]" in system_prompt, "System prompt should include '[RECENT CONTEXT]'"
    assert "[RECURRING THEMES]" in system_prompt, "System prompt should include '[RECURRING THEMES]'"
    assert "Ask 'why' and 'how' more than 'what'" in system_prompt, "System prompt should include emotional exploration"
    print("✓ System prompt is updated correctly.")
    
    print("\nTesting user prompt updates...")
    user_prompt = generator.build_user_prompt(user_context)
    assert "Ask 'why' and 'how' more than 'what'" in user_prompt, "User prompt should include emotional exploration"
    print("✓ User prompt is updated correctly.")

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Model Upgrade and Prompt Updates")
    print("=" * 60)
    
    try:
        test_model_config()
        test_prompt_updates()
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())