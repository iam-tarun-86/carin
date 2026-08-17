import time
import torch
import numpy as np
import sounddevice as sd

# Load Silero VAD once globally to avoid reloading overhead
print("[VAD] Loading Silero Semantic VAD model...")
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

def record_user_speech(sample_rate=16000, silence_duration=0.35, max_speech_duration=12.0) -> np.ndarray:
    """
    Ultra-low-latency Voice Activity Detector (Silero VAD):
    1. 300ms pre-speech rolling ring buffer preserves starting syllables.
    2. Real-time probability tracking + VADIterator for instant ~350ms turn-taking cutoff.
    """
    chunk_samples = 512  # Silero requires 512 samples per chunk at 16kHz (32ms per chunk)
    vad_iterator = VADIterator(model, sampling_rate=sample_rate, min_silence_duration_ms=int(silence_duration * 1000))
    
    print("\n[Microphone] Listening... (speak whenever you're ready)")
    
    pre_speech_buffer = []
    speech_buffer = []
    speaking_started = False
    speech_start_time = None
    silence_chunks = 0
    # ~350ms silence = approx 11 chunks of 512 samples at 16kHz
    max_silence_chunks = int(silence_duration * sample_rate / chunk_samples)
    pre_buffer_max_chunks = int(0.30 * sample_rate / chunk_samples)  # 300ms pre-speech

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32') as stream:
        while True:
            chunk, _ = stream.read(chunk_samples)
            chunk_data = chunk.flatten()
            
            # Silero expects (batch_size, sequence_length) float32 tensor
            chunk_tensor = torch.from_numpy(chunk_data).unsqueeze(0)
            speech_prob = model(chunk_tensor, sample_rate).item()

            if not speaking_started:
                # Rolling pre-speech buffer to catch the start of words
                pre_speech_buffer.append(chunk_data)
                if len(pre_speech_buffer) > pre_buffer_max_chunks:
                    pre_speech_buffer.pop(0)

                if speech_prob > 0.45:
                    speaking_started = True
                    speech_start_time = time.time()
                    # Include the rolling pre-speech buffer
                    speech_buffer.extend(pre_speech_buffer)
                    speech_buffer.append(chunk_data)
                    silence_chunks = 0
                    print("[Microphone] Speech started...")
            else:
                speech_buffer.append(chunk_data)
                
                # Check Silero iterator end event
                vad_state = vad_iterator(torch.from_numpy(chunk_data))
                if vad_state is not None and "end" in vad_state:
                    print("[Microphone] Speech completed (Silero trigger). Transcribing...")
                    break

                # Dual safety: silence threshold counter for instant cutoff
                if speech_prob < 0.35:
                    silence_chunks += 1
                    if silence_chunks >= max_silence_chunks:
                        print("[Microphone] Speech completed (Instant endpoint). Transcribing...")
                        break
                else:
                    silence_chunks = 0

                # Maximum speech duration failsafe
                if (time.time() - speech_start_time) > max_speech_duration:
                    print("[Microphone] Max speech duration reached.")
                    break

    vad_iterator.reset_states()

    if speaking_started and len(speech_buffer) > 0:
        return np.concatenate(speech_buffer)
        
    return np.array([], dtype='float32')
