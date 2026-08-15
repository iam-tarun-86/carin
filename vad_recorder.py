import time
import torch
import numpy as np
import sounddevice as sd

# Load Silero VAD once globally to avoid reloading overhead
print("[VAD] Loading Silero Semantic VAD model...")
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

def record_user_speech(sample_rate=16000, silence_duration=0.5, max_speech_duration=10.0) -> np.ndarray:
    """
    Semantic Voice Activity Detector (Silero):
    1. Uses neural network to detect actual human speech (ignores dog barks, keyboard clacks).
    2. Instantly detects when sentence completes based on linguistic confidence.
    """
    chunk_samples = 512 # Silero requires 512 samples per chunk at 16kHz
    vad_iterator = VADIterator(model, sampling_rate=sample_rate, min_silence_duration_ms=int(silence_duration*1000))
    
    print("\n[Microphone] Listening... (speak whenever you're ready)")
    
    audio_buffer = []
    speaking_started = False
    speech_start_time = None

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32') as stream:
        while True:
            chunk, _ = stream.read(chunk_samples)
            chunk_data = chunk.flatten()
            audio_buffer.append(chunk_data)
            
            # Keep a rolling buffer before speaking starts
            if not speaking_started and len(audio_buffer) > int(sample_rate * 0.3 / chunk_samples):
                audio_buffer.pop(0)

            # Silero expects (batch_size, sequence_length) float32 tensor
            speech_prob = model(torch.from_numpy(chunk_data).unsqueeze(0), sample_rate).item()

            if not speaking_started:
                if speech_prob > 0.5:
                    speaking_started = True
                    speech_start_time = time.time()
                    print("[Microphone] Semantic speech detected...")
            else:
                # Active speech recording phase
                vad_state = vad_iterator(torch.from_numpy(chunk_data))
                if vad_state is not None and not vad_state:
                    # vad_state returns False when speech ends
                    print(f"[Microphone] Semantic turn completed. Transcribing now...")
                    break
                
                # Failsafe timeout
                if (time.time() - speech_start_time) > max_speech_duration:
                    print("[Microphone] Max speech duration reached.")
                    break

    if speaking_started:
        # Reset iterator state for next run
        vad_iterator.reset_states()
        return np.concatenate(audio_buffer)
        
    return np.array([], dtype='float32')
