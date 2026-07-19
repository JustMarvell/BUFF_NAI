import sounddevice as sd
import numpy as np
import webrtcvad
import queue
import time
import wave
from openwakeword.model import Model as WakeModel

from config import SAMPLE_RATE, WAKEWORD_MODELS, VAD_AGGRESSIVENESS, SILENCE_TIMEOUT, FOLLOWUP_TIMEOUT
from modules import mic_lock
from modules.stt import transcribe
from modules.llm import ask_stream
from modules.tts import begin_session, queue_sentence, wait_until_done, is_speaking

CHUNK = 1280        # 80ms @ 16kHz, required by openwakeword
VAD_FRAME = 320      # 20ms @ 16kHz, required by webrtcvad
WAKE_THRESHOLD = 0.5
MIN_RECORD_CHUNKS = 5  # ~0.4s, avoid instant silence-stop

STATE_WAKE = "wake_listening"
STATE_RECORD = "recording"
STATE_PROCESS = "processing"
STATE_FOLLOWUP = "followup"

_audio_q = queue.Queue()

def _callback(indata, frames, time_info, status):
    _audio_q.put(indata[:, 0].copy())

def _has_speech(vad, chunk):
    for i in range(0, len(chunk) - VAD_FRAME + 1, VAD_FRAME):
        if vad.is_speech(chunk[i:i + VAD_FRAME].tobytes(), SAMPLE_RATE):
            return True
    return False

def _save_wav(frames, filename="handsfree_input.wav"):
    audio = np.concatenate(frames, axis=0)
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    return filename

def run():
    if not mic_lock.lock.acquire(blocking=False):
        print("[handsfree] mic busy, aborting")
        return

    wake_model = WakeModel(wakeword_models=WAKEWORD_MODELS, inference_framework="onnx")
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    state = STATE_WAKE
    record_buf = []
    silence_start = None
    followup_start = None

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                             blocksize=CHUNK, callback=_callback)
    stream.start()
    print("[handsfree] listening for wake word... Ctrl+C to stop")

    try:
        while True:
            chunk = _audio_q.get()
            if is_speaking():
                continue  # don't react to NAI's own voice

            if state == STATE_WAKE:
                prediction = wake_model.predict(chunk)
                if any(score > WAKE_THRESHOLD for score in prediction.values()):
                    triggered = max(prediction, key=prediction.get)
                    print(f"[handsfree] wake word: {triggered}")
                    state = STATE_RECORD
                    record_buf, silence_start = [], None

            elif state in (STATE_RECORD, STATE_FOLLOWUP):
                speech = _has_speech(vad, chunk)

                if state == STATE_FOLLOWUP and speech:
                    print("[handsfree] follow-up speech detected")
                    state = STATE_RECORD
                    record_buf, silence_start, followup_start = [], None, None

                if state == STATE_RECORD:
                    record_buf.append(chunk)
                    if speech:
                        silence_start = None
                    elif silence_start is None:
                        silence_start = time.time()
                    elif (time.time() - silence_start > SILENCE_TIMEOUT
                          and len(record_buf) > MIN_RECORD_CHUNKS):
                        state = STATE_PROCESS

                elif state == STATE_FOLLOWUP:
                    if followup_start is None:
                        followup_start = time.time()
                    elif time.time() - followup_start > FOLLOWUP_TIMEOUT:
                        print("[handsfree] follow-up window closed")
                        state, followup_start = STATE_WAKE, None

            if state == STATE_PROCESS:
                filename = _save_wav(record_buf)
                text = transcribe(filename)
                record_buf = []
                if not text:
                    print("[handsfree] nothing transcribed")
                    state = STATE_WAKE
                    continue

                print(f"[handsfree] you said: {text}")
                begin_session()
                try:
                    reply = ask_stream(text, queue_sentence)
                    print(f"[handsfree] NAI: {reply}")
                except ConnectionError as e:
                    print(f"[handsfree] {e}")
                wait_until_done()

                state, followup_start = STATE_FOLLOWUP, time.time()

    except KeyboardInterrupt:
        print("\n[handsfree] stopping")
    finally:
        stream.stop()
        stream.close()
        mic_lock.lock.release()

if __name__ == "__main__":
    from modules.tts import start_worker
    start_worker()
    run()