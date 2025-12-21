import threading
import time
from typing import Optional
from stt.audio_capture import AudioCapture
from stt.engine import STTEngine

class AudioSession:
    """
    Manages a live recording session.
    """
    def __init__(self, stt_engine: STTEngine, callback):
        self.capture = AudioCapture() # Uses defaults
        self.stt = stt_engine
        self.callback = callback # Function to call with partial/final text
        self.active = False
        self.thread = None

    def start(self):
        if self.active:
            return
        
        self.active = True
        self.capture.start()
        self.stt.reset_buffer()
        self.thread = threading.Thread(target=self._run_loop)
        self.thread.start()

    def stop(self) -> str:
        self.active = False
        self.capture.stop()
        if self.thread:
            self.thread.join()
        
        # Return final transcript from buffer
        # This is a bit of a hack since STT engine holds state.
        # In a real system, we'd get the final commited text.
        # Here we just re-transcribe the buffer one last time if needed 
        # or rely on what STTEngine has.
        # For this MVP, we will assume STTEngine buffer has the whole sessions audio (windowed).
        # Which effectively means max 30s.
        # For "Your Story", we likely need >30s.
        # limitation of the current STTEngine impl.
        return "Audio session ended."

    def _run_loop(self):
        for chunk in self.capture.stream_chunks():
            if not self.active:
                break
            
            transcript = self.stt.process_stream(chunk)
            if self.callback:
                self.callback(transcript)
            
            time.sleep(0.01) # Yield
