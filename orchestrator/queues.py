import json
from pathlib import Path
from typing import Dict, Any, Optional

class JobQueue:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def push(self, job_data: Dict[str, Any]):
        """Appends a job to the queue."""
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(job_data) + "\n")

    def peek(self) -> Optional[Dict[str, Any]]:
        """Reads the first job (naive wrapper)."""
        if not self.file_path.exists():
            return None
        
        with open(self.file_path, "r", encoding="utf-8") as f:
            line = f.readline()
            if line:
                return json.loads(line)
        return None

    def pop(self) -> Optional[Dict[str, Any]]:
        """Removes the first job. Requires rewriting file (slow, but ok for MVP)."""
        if not self.file_path.exists():
            return None

        lines = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if not lines:
            return None
            
        job = json.loads(lines[0])
        remaining = lines[1:]
        
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.writelines(remaining)
            
        return job
