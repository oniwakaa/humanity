from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

class OllamaConfig(BaseModel):
    base_url: str = Field(default="http://127.0.0.1:11434", description="Base URL for Ollama API")
    chat_model: str = Field(default="llama3:latest", description="Name of the chat model")
    embed_model: str = Field(default="mxbai-embed-large:latest", description="Name of the embedding model")
    timeout_seconds: float = Field(default=30.0, description="Request timeout in seconds")
    num_ctx: int = Field(default=2048, description="Context window size (tokens)")

class QdrantConfig(BaseModel):
    url: str = Field(default="http://127.0.0.1:6333", description="URL for Qdrant service")
    collection_name: str = Field(default="journal_entries", description="Name of the vector collection")
    api_key: Optional[str] = Field(default=None, description="API key if required")

class STTConfig(BaseModel):
    model_path: str = Field(..., description="Absolute path to the whisper.cpp model file (gguf)")
    device_index: int = Field(default=0, description="Audio input device index")
    sample_rate: int = Field(default=16000, description="Audio sample rate")
    step_duration: float = Field(default=0.5, description="Duration in seconds for streaming step")

class AppConfig(BaseModel):
    ollama: OllamaConfig
    qdrant: QdrantConfig
    stt: STTConfig
    storage_path: str = Field(default="./data", description="Path to store journal entries")

    class Config:
        validate_assignment = True
