import sounddevice as sd
import numpy as np
import queue
from typing import Optional, Generator

class AudioCapture:
    def __init__(self, sample_rate: int = 16000, step_duration: float = 0.5, device_index: Optional[int] = None):
        self.sample_rate = sample_rate
        self.step_duration = step_duration
        self.block_size = int(sample_rate * step_duration)
        self.device_index = device_index
        self.audio_queue = queue.Queue()
        self.running = False
        self.stream: Optional[sd.InputStream] = None

    def _callback(self, indata, frames, time, status):
        """Sounddevice callback."""
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())

    def start(self):
        """Starts the audio stream."""
        if self.running:
            return
        
        self.running = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            device=self.device_index,
            channels=1,
            dtype='float32',
            callback=self._callback
        )
        self.stream.start()

    def stop(self):
        """Stops the audio stream."""
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def stream_chunks(self) -> Generator[np.ndarray, None, None]:
        """Yields audio chunks from the queue."""
        while self.running or not self.audio_queue.empty():
            try:
                # Timeout allows checking self.running periodically
                chunk = self.audio_queue.get(timeout=0.5)
                yield chunk.flatten()
            except queue.Empty:
                continue
