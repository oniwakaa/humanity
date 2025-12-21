class AppError(Exception):
    """Base exception for application errors."""
    pass

class OllamaError(AppError):
    """Base exception for Ollama related errors."""
    pass

class OllamaUnreachableError(OllamaError):
    """Raised when Ollama cannot be reached."""
    pass

class OllamaTimeoutError(OllamaError):
    """Raised when an Ollama request times out."""
    pass

class OllamaModelNotFoundError(OllamaError):
    """Raised when a requested model is not found."""
    pass

class OllamaBadResponseError(OllamaError):
    """Raised when Ollama returns an unexpected response."""
    pass
