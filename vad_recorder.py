import time
import numpy as np
import sounddevice as sd

def record_user_speech(sample_rate=16000, silence_duration=0.6, max_speech_duration=8.0) -> np.ndarray:
    """
    Adaptive Voice Activity Detector:
    1. Calibrates ambient noise floor automatically.
    2. Triggers as soon as speech is detected above ambient noise.
    3. Stops immediately when 0.6s of silence is detected after speaking.
    """
    chunk_samples = int(sample_rate * 0.05) # 50ms chunks
    silence_chunks_needed = int(silence_duration / 0.05)
    
    print("\n[Microphone] Listening... (speak whenever you're ready)")
    
    # Quick 150ms ambient noise calibration
    calibration_chunks = []
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32') as stream:
        for _ in range(3):
            chunk, _ = stream.read(chunk_samples)
            calibration_chunks.append(chunk.flatten())
            
        ambient_rms = np.sqrt(np.mean(np.concatenate(calibration_chunks) ** 2))
        speech_trigger_rms = max(ambient_rms * 2.8, 0.015)
        silence_rms = max(ambient_rms * 1.6, 0.008)

        audio_buffer = list(calibration_chunks)
        speaking_started = False
        silent_chunks = 0
        speech_start_time = None

        while True:
            chunk, _ = stream.read(chunk_samples)
            chunk_data = chunk.flatten()
            energy = np.sqrt(np.mean(chunk_data ** 2))

            if not speaking_started:
                # Waiting for user to start speaking
                if energy > speech_trigger_rms:
                    speaking_started = True
                    speech_start_time = time.time()
                    audio_buffer.append(chunk_data)
                    print("[Microphone] User started speaking...")
                else:
                    # Keep rolling 250ms pre-buffer so start of first word is never clipped
                    audio_buffer.append(chunk_data)
                    if len(audio_buffer) > 5:
                        audio_buffer.pop(0)
            else:
                # Active speech recording phase
                audio_buffer.append(chunk_data)
                if energy < silence_rms:
                    silent_chunks += 1
                else:
                    silent_chunks = 0

                # Stop as soon as user finishes speaking
                if silent_chunks >= silence_chunks_needed:
                    print(f"[Microphone] Silence detected ({silence_duration}s). Transcribing now...")
                    break

                if (time.time() - speech_start_time) > max_speech_duration:
                    print("[Microphone] Max speech duration reached.")
                    break

    if audio_buffer and speaking_started:
        return np.concatenate(audio_buffer)
    return np.array([], dtype='float32')
