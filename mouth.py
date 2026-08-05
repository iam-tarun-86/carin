import re
import time
import queue
import threading
import sounddevice as sd
import numpy as np
from kokoro import KPipeline

import os
os.environ["HF_HUB_OFFLINE"] = "1"

class Mouth:
    def __init__(self, lang_code: str = 'a', voice: str = 'af_heart'):
        print("[Mouth] Initializing Kokoro-82M TTS Pipeline...")
        self.pipeline = KPipeline(lang_code=lang_code, repo_id='hexgrad/Kokoro-82M')
        self.voice = voice
        self.sample_rate = 24000
        self.audio_queue = queue.Queue()
        self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()
        print("[Mouth] TTS Pipeline ready.")

    def _playback_worker(self):
        from state_manager import state_manager
        while True:
            item = self.audio_queue.get()
            if item is None:
                break
            
            # Unpack audio data and sentence emotion if provided
            if isinstance(item, tuple):
                audio_data, sentence_emotion = item
            else:
                audio_data, sentence_emotion = item, None

            if sentence_emotion:
                state_manager.set_emotion(sentence_emotion)
                
            state_manager.set_state("speaking")
            
            # Stream playback in small frame chunks to calculate real-time viseme openness
            frame_size = int(self.sample_rate * 0.04) # 40ms frame chunks (25 fps sync)
            total_samples = len(audio_data)
            
            sd.play(audio_data, samplerate=self.sample_rate)
            
            # Broadcast frame energy levels synchronized with playback loop
            for offset in range(0, total_samples, frame_size):
                chunk = audio_data[offset:offset + frame_size]
                rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
                openness = min(1.0, rms * 12.0) # Normalized openness multiplier
                state_manager.send_viseme(loudness=rms, mouth_openness=openness)
                time.sleep(0.04)
                
            sd.wait()
            state_manager.send_viseme(loudness=0.0, mouth_openness=0.0)
            self.audio_queue.task_done()
            if self.audio_queue.empty():
                state_manager.set_state("idle")

    def speak_sentence(self, text: str, emotion: str = None):
        if not text.strip():
            return
        generator = self.pipeline(text, voice=self.voice, speed=1.1, split_pattern=r'\n+')
        for gs, ps, audio in generator:
            if audio is not None:
                # audio is a torch Tensor or numpy array
                if hasattr(audio, 'numpy'):
                    audio_np = audio.numpy()
                else:
                    audio_np = np.array(audio)
                self.audio_queue.put((audio_np, emotion))

    def wait_until_done(self):
        self.audio_queue.join()

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
