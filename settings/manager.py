import json
import os
from pathlib import Path
from typing import Optional
from .config_model import AppConfig

CONFIG_FILE_NAME = "config.json"

class SettingsManager:
    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self.config_path = self.config_dir / CONFIG_FILE_NAME
        self._config: Optional[AppConfig] = None

    def load_settings(self) -> AppConfig:
        """Loads settings from the config file, or raises FileNotFoundError if not exists."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found at {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            data = json.load(f)
        
        self._config = AppConfig(**data)
        return self._config

    def save_settings(self, config: AppConfig):
        """Saves the configuration to the file."""
        self._config = config
        with open(self.config_path, 'w') as f:
            f.write(config.model_dump_json(indent=4))
    
    def get_config(self) -> AppConfig:
        if self._config is None:
            return self.load_settings()
        return self._config

    def exists(self) -> bool:
        return self.config_path.exists()
