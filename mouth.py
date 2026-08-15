import re
import time
import queue
import threading
import sounddevice as sd
import numpy as np

import os
os.environ["HF_HUB_OFFLINE"] = "1"

import httpx

class Mouth:
    def __init__(self, voice: str = 'en-US-JennyNeural'):
        print("[Mouth] Initializing Pocket TTS Pipeline (CPU)...")
        self.api_url = "http://localhost:8086/v1/audio/speech"
        self.voice = voice
        self.sample_rate = 24000
        
        # Audio buffer for active streaming playback
        self.playback_buffer = np.array([], dtype='float32')
        self.buffer_lock = threading.Lock()
        self.is_synthesizing = False
        
        # Open continuous async stream
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            callback=self._audio_callback,
            blocksize=1024 # ~42ms blocks
        )
        self.stream.start()
        print("[Mouth] Pocket TTS Pipeline and Audio Stream ready.")

    def _audio_callback(self, outdata, frames, time_info, status):
        from state_manager import state_manager
        with self.buffer_lock:
            available = len(self.playback_buffer)
            if available > 0:
                take = min(available, frames)
                chunk = self.playback_buffer[:take]
                self.playback_buffer = self.playback_buffer[take:]
                
                outdata[:take, 0] = chunk
                if take < frames:
                    outdata[take:, 0] = 0
                
                # Calculate amplitude
                rms = float(np.sqrt(np.mean(chunk ** 2)))
                state_manager.send_audio_amplitude(rms)
                state_manager.set_state("speaking")
            else:
                outdata[:, 0] = 0
                state_manager.send_audio_amplitude(0.0)

    def speak_sentence(self, text: str, emotion: str = None):
        if not text.strip():
            return
        
        from state_manager import state_manager
        if emotion:
            state_manager.set_emotion(emotion)
            
        self.is_synthesizing = True
        try:
            payload = {
                "model": "pocket-tts-v1",
                "input": text,
                "voice": self.voice,
                "response_format": "pcm"
            }
            # Stream raw PCM chunks directly from Pocket TTS server
            with httpx.Client() as client:
                with client.stream("POST", self.api_url, json=payload, timeout=10.0) as response:
                    if response.status_code == 200:
                        for chunk in response.iter_bytes(chunk_size=4096):
                            if chunk:
                                # Convert int16 PCM bytes to float32 numpy array
                                audio_np = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                                with self.buffer_lock:
                                    self.playback_buffer = np.concatenate([self.playback_buffer, audio_np])
                    else:
                        print(f"[Mouth Error] Pocket TTS returned {response.status_code}")
        except Exception as e:
            print(f"[Mouth Error] Failed to connect to Pocket TTS: {e}")
        finally:
            self.is_synthesizing = False

    def wait_until_done(self):
        while True:
            with self.buffer_lock:
                if len(self.playback_buffer) == 0 and not self.is_synthesizing:
                    break
            time.sleep(0.05)

class SentenceStreamBuffer:
    def __init__(self, mouth_instance: Mouth):
        self.mouth = mouth_instance
        self.buffer = ""
        self.current_emotion = "neutral"
        # Punctuation regex for split boundaries
        self.sentence_end_pattern = re.compile(r'([.!?\n]+)')
        self.emotion_pattern = re.compile(r'\[(happy|sad|surprised|excited|angry|hesitant|refusing|neutral)\]', re.IGNORECASE)

    def push_token(self, token: str):
        self.buffer += token
        
        # Check if new token updates current sentence emotion
        emo_match = self.emotion_pattern.search(token)
        if emo_match:
            self.current_emotion = emo_match.group(1).lower()

        parts = self.sentence_end_pattern.split(self.buffer)
        
        # If we have complete sentence parts + remainder
        if len(parts) > 1:
            # Reconstruct sentences up to the last split
            for i in range(0, len(parts) - 1, 2):
                sentence = parts[i] + parts[i+1]
                # Strip inline emotion tags before TTS synthesis
                clean_sentence = self.emotion_pattern.sub('', sentence).strip()
                if clean_sentence:
                    print(f"\n[Mouth Synthesis Trigger] [{self.current_emotion.upper()}] '{clean_sentence}'")
                    self.mouth.speak_sentence(clean_sentence, emotion=self.current_emotion)
            self.buffer = parts[-1]

    def flush(self):
        clean_sentence = self.emotion_pattern.sub('', self.buffer).strip()
        if clean_sentence:
            print(f"\n[Mouth Synthesis Flush] [{self.current_emotion.upper()}] '{clean_sentence}'")
            self.mouth.speak_sentence(clean_sentence, emotion=self.current_emotion)
            self.buffer = ""

if __name__ == "__main__":
    mouth = Mouth()
    print("[Mouth] Test module ready.")
