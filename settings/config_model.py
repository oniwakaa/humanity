from pydantic import BaseModel, HttpUrl, Field, ConfigDict
from typing import Optional

class OllamaConfig(BaseModel):
    base_url: str = Field(default="http://127.0.0.1:11434", description="Base URL for Ollama API")
    chat_model: str = Field(default="hf.co/unsloth/SmolLM3-3B-GGUF:Q4_K_M", description="Name of the chat model")
    embed_model: str = Field(default="mxbai-embed-large:latest", description="Name of the embedding model")
    timeout_seconds: float = Field(default=30.0, description="Request timeout in seconds")
    num_ctx: int = Field(default=2048, description="Context window size (tokens)")

# QdrantConfig removed


class STTConfig(BaseModel):
    model_path: str = Field(..., description="Absolute path to the whisper.cpp model file (gguf)")
    device_index: int = Field(default=0, description="Audio input device index")
    sample_rate: int = Field(default=16000, description="Audio sample rate")
    step_duration: float = Field(default=0.5, description="Duration in seconds for streaming step")

class AppConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    ollama: OllamaConfig
    # qdrant: QdrantConfig # Removed in favor of embedded Chroma

    stt: STTConfig
    storage_path: str = Field(default="./data", description="Path to store journal entries")
