import logging
from logging.handlers import RotatingFileHandler
from user_secrets import get_secret # Hypothetical safe import or just standard logging

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
