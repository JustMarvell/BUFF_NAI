import sounddevice as sd
import numpy as np
import webrtcvad
import queue
import time
import wave
import threading
from openwakeword.model import Model as WakeModel

from config import SAMPLE_RATE, WAKEWORD_MODELS, VAD_AGGRESSIVENESS, SILENCE_TIMEOUT, FOLLOWUP_TIMEOUT
from modules import mic_lock, request_queue
from modules.stt import transcribe
from modules.tts import queue_sentence, wait_until_done, is_speaking
from modules.persistence import append_entry

CHUNK = 1280        # 80ms @ 16kHz, required by openwakeword
VAD_FRAME = 320      # 20ms @ 16kHz, required by webrtcvad
WAKE_THRESHOLD = 0.5
MIN_RECORD_CHUNKS = 10  # ~0.8s, avoid instant silence-stop
NOISE_GATE_MULTIPLIER = 1.5     # speech must be this many x louder than ambient noise || 1.5 for now is good, but it still picking up static sometimes
                                # further testing is required.
CALIBRATION_SEC = 2.0
INITIAL_SPEECH_TIMEOUT = 4.0  # give up if no speech at all within this long

STATE_WAKE = "wake_listening"
STATE_RECORD = "recording"
STATE_PROCESS = "processing"
STATE_FOLLOWUP = "followup"
STATE_OFF = "off"

_audio_q = queue.Queue()
_stop_flag = threading.Event()
_state = STATE_OFF
_level = 0.0

def get_state():
    return _state

def get_level():
    return _level

def is_running():
    return _state != STATE_OFF

def stop():
    _stop_flag.set()

def _callback(indata, frames, time_info, status):
    global _level
    chunk = indata[:, 0].copy()
    _audio_q.put(chunk)
    _level = min(np.abs(chunk).mean() / 4000, 1.0)

def _has_speech(vad, chunk, gate_threshold):
    if np.abs(chunk.astype(np.float32)).mean() < gate_threshold:
        return False
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

def _calibrate_noise_floor(stream_q, chunks_needed):
    levels = []
    while len(levels) < chunks_needed:
        chunk = stream_q.get()
        levels.append(np.abs(chunk.astype(np.float32)).mean())
    return float(np.median(levels))

def run(on_status=None, on_conversation=None):
    """Blocking. Run in a background thread; call stop() to end."""
    global _state, _level
    if not mic_lock.lock.acquire(blocking=False):
        if on_status:
            on_status("Mic busy, can't start hands-free.")
        return

    _stop_flag.clear()
    wake_model = WakeModel(wakeword_models=WAKEWORD_MODELS, inference_framework="onnx")
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    _state = STATE_WAKE
    record_buf, silence_start, followup_start = [], None, None
    heard_speech = False
    record_start = None

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                             blocksize=CHUNK, callback=_callback)
    stream.start()
    if on_status:
        on_status("Calibrating noise floor...")
    noise_floor = _calibrate_noise_floor(_audio_q, int(CALIBRATION_SEC * SAMPLE_RATE / CHUNK))
    gate_threshold = max(noise_floor * NOISE_GATE_MULTIPLIER, 50)
    print(f"[handsfree] noise_floor={noise_floor:.1f} gate_threshold={gate_threshold:.1f}")
    if on_status:
        on_status("Hands-free: listening for wake word")

    try:
        while not _stop_flag.is_set():
            try:
                chunk = _audio_q.get(timeout=0.5)
            except queue.Empty:
                continue
            if is_speaking():
                continue

            if _state == STATE_WAKE:
                prediction = wake_model.predict(chunk)
                if any(score > WAKE_THRESHOLD for score in prediction.values()):
                    triggered = max(prediction, key=prediction.get)
                    _state = STATE_RECORD
                    record_buf, silence_start = [], None
                    heard_speech = False
                    record_start = time.time()
                    if on_status:
                        on_status(f"Wake word: {triggered}")

            elif _state in (STATE_RECORD, STATE_FOLLOWUP):
                speech = _has_speech(vad, chunk, gate_threshold)

                if _state == STATE_FOLLOWUP and speech:
                    _state = STATE_RECORD
                    record_buf, silence_start, followup_start = [], None, None
                    heard_speech = False
                    record_start = time.time()
                    if on_status:
                        on_status("Listening...")

                if _state == STATE_RECORD:
                    record_buf.append(chunk)
                    amp = np.abs(chunk.astype(np.float32)).mean()
                    print(f"[handsfree] amp={amp:.1f} gate={gate_threshold:.1f} speech={speech}")
                    if speech:
                        heard_speech = True
                        silence_start = None
                    elif heard_speech and silence_start is None:
                        silence_start = time.time()
                    elif heard_speech and time.time() - silence_start > SILENCE_TIMEOUT:
                        _state = STATE_PROCESS
                    elif not heard_speech and time.time() - record_start > INITIAL_SPEECH_TIMEOUT:
                        # gave up, nothing was said
                        _state = STATE_WAKE
                        record_buf = []
                        if on_status:
                            on_status("No speech heard, listening for wake word")

                elif _state == STATE_FOLLOWUP:
                    if followup_start is None:
                        followup_start = time.time()
                    elif time.time() - followup_start > FOLLOWUP_TIMEOUT:
                        _state, followup_start = STATE_WAKE, None
                        if on_status:
                            on_status("Hands-free: listening for wake word")

            if _state == STATE_PROCESS:
                filename = _save_wav(record_buf)
                text = transcribe(filename)
                record_buf = []
                if not text:
                    _state = STATE_WAKE
                    if on_status:
                        on_status("Nothing heard, listening for wake word")
                    continue

                user_entry = append_entry("user", text, source="handsfree")
                if on_conversation:
                    on_conversation(f"[{user_entry['timestamp']}] You: {text}\n", "user")
                if on_status:
                    on_status(f"You: {text}")

                done_event = threading.Event()
                ai_started = False

                def on_sentence(s):
                    nonlocal ai_started
                    if on_conversation:
                        if not ai_started:
                            on_conversation(f"[{time.strftime('%H:%M:%S')}] NAI: ", "ai")
                            ai_started = True
                        else:
                            on_conversation(" ", "ai")
                        on_conversation(s, "ai")
                    queue_sentence(s)

                def on_done(full_reply):
                    append_entry("ai", full_reply, source="handsfree")
                    if on_conversation:
                        on_conversation("\n\n", None)
                    done_event.set()

                def on_error(e):
                    if on_status:
                        on_status(f"Error: {e}")
                    done_event.set()

                request_queue.submit(text, "handsfree", on_sentence, on_done, on_error)
                done_event.wait()
                wait_until_done()

                _state, followup_start = STATE_FOLLOWUP, time.time()
                if on_status:
                    on_status("Follow-up window...")

    finally:
        stream.stop()
        stream.close()
        mic_lock.lock.release()
        _state = STATE_OFF
        if on_status:
            on_status("Hands-free stopped")

if __name__ == "__main__":
    from modules.tts import start_worker
    start_worker()
    request_queue.start_worker()
    run(on_status=print)