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
    def __init__(self, voice: str = 'anna'):
        print(f"[Mouth] Initializing Pocket TTS Pipeline (Voice: {voice})...")
        self.api_url = "http://localhost:8086/tts"
        self.voice = voice
        self.sample_rate = 24000
        
        # Audio buffer for active streaming playback
        self.playback_buffer = np.array([], dtype='float32')
        self.buffer_lock = threading.Lock()
        
        # Async synthesis queue and worker
        self.tts_queue = queue.Queue()
        self.is_active = True
        self.synthesis_worker_thread = threading.Thread(target=self._synthesis_worker, daemon=True)
        self.synthesis_worker_thread.start()
        
        # Open continuous async stream
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            callback=self._audio_callback,
            blocksize=1024 # ~42ms blocks
        )
        self.stream.start()
        print(f"[Mouth] Pocket TTS Async Pipeline ready ({voice} female voice).")

    def _synthesis_worker(self):
        """Dedicated background thread to query Pocket TTS without blocking the LLM or audio callback."""
        from state_manager import state_manager
        with httpx.Client(timeout=15.0) as client:
            while self.is_active:
                try:
                    item = self.tts_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                if item is None:
                    break

                text, emotion = item
                if not text.strip():
                    self.tts_queue.task_done()
                    continue

                if emotion:
                    state_manager.set_emotion(emotion)

                try:
                    data = {
                        "text": text,
                        "voice_url": self.voice
                    }
                    response = client.post(self.api_url, data=data)
                    if response.status_code == 200:
                        audio_np, sr = sf.read(io.BytesIO(response.content), dtype='float32')
                        if audio_np.ndim > 1:
                            audio_np = audio_np[:, 0] # mono

                        # Apply quick 5ms edge smoothing to eliminate boundary click/pop
                        fade_len = min(len(audio_np), int(self.sample_rate * 0.005))
                        if fade_len > 0:
                            fade_in = np.linspace(0.0, 1.0, fade_len, dtype='float32')
                            fade_out = np.linspace(1.0, 0.0, fade_len, dtype='float32')
                            audio_np[:fade_len] *= fade_in
                            audio_np[-fade_len:] *= fade_out

                        with self.buffer_lock:
                            self.playback_buffer = np.concatenate([self.playback_buffer, audio_np])
                    else:
                        print(f"[Mouth Error] Pocket TTS returned {response.status_code}: {response.text}")
                except Exception as e:
                    print(f"[Mouth Error] Failed to synthesize chunk: {e}")
                finally:
                    self.tts_queue.task_done()

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
        """Enqueues sentence for async background synthesis without blocking the streaming loop."""
        if text.strip():
            self.tts_queue.put((text, emotion))

    def wait_until_done(self):
        self.tts_queue.join()
        while True:
            with self.buffer_lock:
                if len(self.playback_buffer) == 0 and self.tts_queue.empty():
                    break
            time.sleep(0.04)

    def close(self):
        """Cleanly terminates audio stream and worker thread."""
        self.is_active = False
        try:
            self.tts_queue.put_nowait(None)
        except Exception:
            pass
        try:
            if hasattr(self, 'stream') and self.stream:
                self.stream.stop()
                self.stream.close()
        except Exception:
            pass

class SentenceStreamBuffer:
    def __init__(self, mouth_instance: Mouth):
        self.mouth = mouth_instance
        self.buffer = ""
        self.current_emotion = "neutral"
        # Punctuation regex for split boundaries
        self.sentence_end_pattern = re.compile(r'([.!?\n]+)')
        self.emotion_pattern = re.compile(r'\[([a-zA-Z_-]+)\]')
        self.emotion_map = {
            "happy": "happy", "joy": "happy", "joyful": "happy", "cheerful": "happy", "smile": "happy", "smiles": "happy", "grin": "happy", "grinning": "happy", "laugh": "happy", "chuckle": "happy", "giggle": "happy", "wink": "happy",
            "excited": "excited", "enthusiastic": "excited", "energetic": "excited", "amazed": "excited",
            "sad": "sad", "empathetic": "sad", "sympathetic": "sad", "sorrowful": "sad", "concerned": "sad", "teary-eyed": "sad", "crying": "sad", "gloomy": "sad",
            "surprised": "surprised", "shocked": "surprised", "curious": "surprised", "astonished": "surprised",
            "angry": "angry", "annoyed": "angry", "frustrated": "angry", "irritated": "angry",
            "hesitant": "hesitant", "nervous": "hesitant", "thoughtful": "hesitant", "confused": "hesitant", "uncertain": "hesitant", "puzzled": "hesitant",
            "refusing": "refusing", "stern": "refusing", "disagree": "refusing", "denying": "refusing",
            "neutral": "neutral", "calm": "neutral", "relaxed": "neutral"
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
