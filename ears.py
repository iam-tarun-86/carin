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
        """
        start = time.time()
        # whisper expects float32 numpy array normalized to [-1, 1]
        result = self.model.transcribe(audio_data, language="en", fp16=(self.device == "cuda"))
        text = result.get("text", "").strip()
        latency = (time.time() - start) * 1000
        print(f"[Ears] Transcribed in {latency:.1f}ms: '{text}'")
        return text

if __name__ == "__main__":
    ears = Ears()
    print("[Ears Test] PyTorch Whisper Engine ready.")
