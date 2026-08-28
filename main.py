import os
import sys
import warnings
import logging

# Suppress all library warnings and verbose logs
warnings.filterwarnings("ignore")
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("uvicorn").setLevel(logging.WARNING)

# Suppress Hugging Face Symlink Warning and enable offline mode on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTHONWARNINGS"] = "ignore"

# Add all nvidia bin directories to DLL search path for CTranslate2 / PyTorch
nvidia_base = os.path.join(os.path.dirname(__file__), "venv311", "Lib", "site-packages", "nvidia")
if os.path.exists(nvidia_base):
    for root, dirs, files in os.walk(nvidia_base):
        if "bin" in dirs:
            bin_path = os.path.abspath(os.path.join(root, "bin"))
            os.environ["PATH"] = bin_path + os.path.pathsep + os.environ.get("PATH", "")
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(bin_path)
                except Exception:
                    pass

import time
import numpy as np
import sounddevice as sd
from ears import Ears
from brain import Brain
from mouth import Mouth, SentenceStreamBuffer
from vad_recorder import record_user_speech

def main():
    print("=" * 60)
    print("      ZERO-LATENCY NATIVE WINDOWS VOICE AGENT")
    print("=" * 60)

    # Initialize Stages
    from state_manager import state_manager
    state_manager.start()

    # Automatically open the Web UI dashboard
    try:
        import webbrowser
        webbrowser.open("http://localhost:5173")
        print("[Orchestrator] Opened Web UI in default browser.")
    except Exception as e:
        print(f"[Orchestrator Warning] Failed to open Web UI automatically: {e}")

    ears = Ears(model_size="turbo", device="cuda", compute_type="float32")
    brain = Brain(api_url="http://localhost:8085/v1/chat/completions")
    mouth = Mouth(voice="anna")

    def on_voice_change(new_voice):
        print(f"[Orchestrator] Changing TTS voice to: {new_voice}")
        mouth.voice = new_voice

    state_manager.register_voice_callback(on_voice_change)

    print("\n[Orchestrator] System initialized and ready!")

    try:
        while True:
            try:
                # 1. Ear Stage: Auto-Adaptive VAD Capture & Transcribe
                state_manager.set_state("listening")
                audio_buffer = record_user_speech()
                if audio_buffer.size == 0:
                    continue

                state_manager.set_state("thinking")
                user_text = ears.transcribe_audio_buffer(audio_buffer)

                if not user_text:
                    print("[Orchestrator] No speech recognized. Listening again...")
                    continue

                print(f"\n[USER]: {user_text}")
                if user_text.lower().strip() in ["exit", "quit", "stop", "goodbye"]:
                    print("[Orchestrator] Exiting voice agent loop. Goodbye!")
                    break

                # 2 & 3. Brain & Mouth Stage: Stream tokens -> Synthesize sentences
                sentence_buffer = SentenceStreamBuffer(mouth)
                print("[ASSISTANT]: ", end="", flush=True)

                token_count = 0
                start_time = time.time()
                first_token_time = None

                for token in brain.stream_chat(user_text):
                    if first_token_time is None:
                        first_token_time = (time.time() - start_time) * 1000
                    print(token, end="", flush=True)
                    sentence_buffer.push_token(token)
                    token_count += 1

                sentence_buffer.flush()
                mouth.wait_until_done()
                state_manager.set_state("idle")

                if first_token_time is not None:
                    print(f"\n[Latency Metrics] Time to First Token (TTFT): {first_token_time:.1f}ms")

            except KeyboardInterrupt:
                print("\n[Orchestrator] Shutting down...")
                break
            except Exception as e:
                print(f"\n[Orchestrator Error]: {e}")
    finally:
        print("[Orchestrator] Releasing audio and background resources...")
        mouth.close()
        state_manager.set_state("offline")
        print("[Orchestrator] Clean exit complete.")

if __name__ == "__main__":
    main()
