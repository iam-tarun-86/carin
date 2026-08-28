import time
import torch
import whisper
import numpy as np

class Ears:
    def __init__(self, model_size="turbo", device=None, compute_type=None):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Ears] Loading OpenAI PyTorch Whisper model '{model_size}' on {self.device}...")
        self.model = whisper.load_model(model_size, device=self.device)
        print("[Ears] STT Engine ready (PyTorch CUDA).")

    def transcribe_audio_buffer(self, audio_data: np.ndarray, sampling_rate: int = 16000) -> str:
        """
        Transcribe a float32 numpy array audio buffer using PyTorch CUDA.
        Guarded against silence hallucinations, repetition loops, and noise artifacts.
        """
        if audio_data is None or len(audio_data) < int(sampling_rate * 0.3):
            return ""

        # 1. Noise floor RMS energy check (prevent transcribing pure background silence)
        rms = float(np.sqrt(np.mean(audio_data ** 2)))
        if rms < 0.008:
            return ""

        start = time.time()
        
        # 2. Strict hallucination-immune Whisper decoding parameters
        result = self.model.transcribe(
            audio_data,
            language="en",
            fp16=(self.device == "cuda"),
            temperature=0.0,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
            logprob_threshold=-1.0
        )
        
        text = result.get("text", "").strip()

        # 3. Known phantom subtitle / static hallucinations filter
        phantom_hallucinations = {
            "thank you.", "thank you", "thanks for watching!", "subtitles by",
            "you", ".", "..", "...", "listening", "listening, listening"
        }
        if text.lower() in phantom_hallucinations and rms < 0.02:
            return ""

        latency = (time.time() - start) * 1000
        if text:
            print(f"[Ears] Transcribed in {latency:.1f}ms (RMS: {rms:.4f}): '{text}'")
        return text

if __name__ == "__main__":
    ears = Ears()
    print("[Ears Test] PyTorch Whisper Engine ready.")
