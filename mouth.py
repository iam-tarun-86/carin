import re
import time
import queue
import threading
import sounddevice as sd
import numpy as np

import os
os.environ["HF_HUB_OFFLINE"] = "1"

import io
import soundfile as sf
import httpx

class Mouth:
    def __init__(self, voice: str = 'alba'):
        print("[Mouth] Initializing Pocket TTS Pipeline...")
        self.api_url = "http://localhost:8086/tts"
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
            # Pocket TTS accepts form data with 'text'
            data = {"text": text}
            with httpx.Client(timeout=15.0) as client:
                response = client.post(self.api_url, data=data)
                if response.status_code == 200:
                    # Decode WAV audio stream to float32 numpy array
                    audio_np, sr = sf.read(io.BytesIO(response.content), dtype='float32')
                    if audio_np.ndim > 1:
                        audio_np = audio_np[:, 0] # mono
                    
                    with self.buffer_lock:
                        self.playback_buffer = np.concatenate([self.playback_buffer, audio_np])
                else:
                    print(f"[Mouth Error] Pocket TTS returned {response.status_code}: {response.text}")
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
        self.emotion_pattern = re.compile(r'\[([a-zA-Z_-]+)\]')
        self.emotion_map = {
            "happy": "happy", "joy": "happy", "joyful": "happy", "cheerful": "happy",
            "excited": "excited", "enthusiastic": "excited", "energetic": "excited",
            "sad": "sad", "empathetic": "sad", "sympathetic": "sad", "sorrowful": "sad",
            "surprised": "surprised", "shocked": "surprised", "curious": "surprised",
            "angry": "angry", "annoyed": "angry", "frustrated": "angry",
            "hesitant": "hesitant", "nervous": "hesitant", "thoughtful": "hesitant",
            "refusing": "refusing", "stern": "refusing", "disagree": "refusing",
            "neutral": "neutral", "calm": "neutral"
        }

    def push_token(self, token: str):
        self.buffer += token
        
        # Check if new token updates current sentence emotion
        emo_match = self.emotion_pattern.search(token)
        if emo_match:
            raw_emo = emo_match.group(1).lower()
            if raw_emo in self.emotion_map:
                self.current_emotion = self.emotion_map[raw_emo]

        parts = self.sentence_end_pattern.split(self.buffer)
        
        # If we have complete sentence parts + remainder
        if len(parts) > 1:
            # Reconstruct sentences up to the last split
            for i in range(0, len(parts) - 1, 2):
                sentence = parts[i] + parts[i+1]
                # Strip any inline [emotion] tags before TTS synthesis
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
