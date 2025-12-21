import numpy as np
from typing import Optional, List
from pathlib import Path

# Try importing pywhispercpp, mock if not available for dev setup
try:
    from pywhispercpp.model import Model
except ImportError:
    Model = None

class STTEngine:
    def __init__(self, model_path: str, context_window: int = 30):
        self.model_path = model_path
        self.context_window = context_window
        self.model = None
        self._buffer = np.array([], dtype='float32')

    def load_model(self):
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        if Model:
            # n_threads could be configurable
            self.model = Model(self.model_path, n_threads=4, print_realtime=False, print_progress=False)
        else:
            print("Warning: pywhispercpp not installed. STT will not work.")

    def process_stream(self, audio_chunk: np.ndarray) -> str:
        """
        Receives a chunk of audio, updates buffer, runs inference.
        Returns the current partial transcript.
        
        Real Implementation:
        1. Accumulate audio.
        2. Detect silence (simple energy threshold).
        3. If silence persists, consider segment finalized (in a real system, we'd emit a 'final' event).
           For this MVP, we just transcribe the standard buffer.
        """
        # Append new chunk
        self._buffer = np.concatenate((self._buffer, audio_chunk))
        
        # Simple VAD (Energy Based)
        # Calculate RMS energy of the last chunk
        rms = np.sqrt(np.mean(audio_chunk**2))
        silence_threshold = 0.01 # Tunable
        
        # In a generic loop, we might buffer until silence, then transcribe.
        # But 'process_stream' implies continuous partial updates.
        # So we should transcribe the *whole* valid buffer (or last N seconds)
        # to get the current context.
        # To avoid re-transcribing minutes of audio, we should keep a sliding window.
        
        # Limit buffer to contact_window (e.g., 30s)
        max_samples = 16000 * self.context_window
        if len(self._buffer) > max_samples:
             self._buffer = self._buffer[-max_samples:]
        
        # Run inference on current buffer
        if self.model and len(self._buffer) > 16000: # Wait for 1 sec of audio
             try:
                 # Standard inference. 
                 # To support proper "partial" vs "final", we'd use the stream API.
                 # Using standard transcribe on the buffer gives "what was said so far".
                 segments = self.model.transcribe(self._buffer, new_segment_callback=None)
                 text = " ".join([s.text for s in segments])
                 return text.strip()
             except Exception as e:
                 print(f"STT Error: {e}")
                 return "..."
        
        return "..."

    def reset_buffer(self):
        self._buffer = np.array([], dtype='float32')
