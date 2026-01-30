import logging
from logging.handlers import RotatingFileHandler

class TelemetryLogger:
    def __init__(self, log_dir: str = "./logs"):
        self.logger = logging.getLogger("humanity_telemetry")
        self.logger.setLevel(logging.INFO)
        
        # Prevent double configuration
        if not self.logger.handlers:
            handler = RotatingFileHandler(
                f"{log_dir}/telemetry.log", 
                maxBytes=1024*1024, # 1MB
                backupCount=3
            )
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_event(self, event_type: str, metrics: dict):
        """
        Logs a structured event.
        CRITICAL: Do NOT log raw user text content.
        """
        # Sanitize metrics just in case
        safe_metrics = {k: v for k, v in metrics.items() if k not in ["text", "audio", "transcript"]}
        
        self.logger.info(f"EVENT: {event_type} - {safe_metrics}")

    def log_error(self, error_type: str, message: str):
        self.logger.error(f"ERROR: {error_type} - {message}")

# Simple module-level logger factory
_logger_cache = {}

def get_logger(name: str) -> logging.Logger:
    """Get or create a logger for the given module name."""
    if name not in _logger_cache:
        logger = logging.getLogger(name)
        # Only add handler if not already configured
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.WARNING)
            formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.WARNING)
        _logger_cache[name] = logger
    return _logger_cache[name]
