import subprocess
import queue
import threading
import tempfile
import os
import sys
import time
import numpy as np
from scipy.io.wavfile import read as wav_read
from config import PIPER_MODEL

PIPER_BIN = os.path.join(os.path.dirname(sys.executable), "piper")
if not os.path.exists(PIPER_BIN):
    PIPER_BIN = "piper"

_play_process = None
_sentence_queue = queue.Queue()
_audio_queue = queue.Queue()
_stop_flag = threading.Event()
_workers_started = False

_ENV_CHUNK_SEC = 0.03
_tts_envelope = None
_tts_duration = 0.0
_tts_start = None

def _compute_envelope(path, chunk_ms=30):
    rate, data = wav_read(path)
    data = data.astype(np.float32)
    if data.ndim > 1:
        data = data.mean(axis=1)
    chunk_size = max(1, int(rate * chunk_ms / 1000))
    n_chunks = max(1, len(data) // chunk_size)
    levels = []
    for i in range(n_chunks):
        seg = data[i * chunk_size:(i + 1) * chunk_size]
        levels.append(np.sqrt(np.mean(seg ** 2)) if len(seg) else 0.0)
    peak = max(levels) or 1.0
    levels = [min(l / peak, 1.0) for l in levels]
    duration = len(data) / rate
    return levels, duration

def _synth_worker():
    while True:
        text = _sentence_queue.get()
        if not _stop_flag.is_set():
            try:
                fd, path = tempfile.mkstemp(suffix=".wav")
                os.close(fd)
                result = subprocess.run(
                    [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", path],
                    input=text, text=True, capture_output=True, timeout=30
                )
                if result.returncode != 0:
                    print(f"Piper failed: {result.stderr.strip()}")
                    os.remove(path)
                elif _stop_flag.is_set():
                    os.remove(path)
                else:
                    envelope, duration = _compute_envelope(path)
                    _audio_queue.put((path, envelope, duration))
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                print(f"TTS synth error: {e}")
        _sentence_queue.task_done()

def _play_worker():
    global _play_process, _tts_envelope, _tts_duration, _tts_start
    while True:
        path, envelope, duration = _audio_queue.get()
        if not _stop_flag.is_set():
            try:
                _tts_envelope = envelope
                _tts_duration = duration
                _tts_start = time.time()
                _play_process = subprocess.Popen(["aplay", path])
                _play_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
            finally:
                _play_process = None
                _tts_envelope = None
                _tts_start = None
        if os.path.exists(path):
            os.remove(path)
        _audio_queue.task_done()

def start_worker():
    global _workers_started
    if not _workers_started:
        threading.Thread(target=_synth_worker, daemon=True).start()
        threading.Thread(target=_play_worker, daemon=True).start()
        _workers_started = True

def begin_session():
    _stop_flag.clear()

def queue_sentence(text):
    _sentence_queue.put(text)

def wait_until_done():
    _sentence_queue.join()
    _audio_queue.join()

def speak(text, filename="output.wav", timeout=30):
    """Non-streaming single-shot speak, kept for compatibility."""
    result = subprocess.run(
        [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", filename],
        input=text, text=True, capture_output=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(f"Piper failed: {result.stderr.strip()}")
    subprocess.run(["aplay", filename], timeout=timeout)

def is_speaking():
    return _play_process is not None

def get_tts_level():
    if _tts_envelope is None or _tts_start is None:
        return 0.0
    idx = int((time.time() - _tts_start) / _ENV_CHUNK_SEC)
    if idx >= len(_tts_envelope):
        return 0.0
    return _tts_envelope[idx]

def stop_speaking():
    global _tts_envelope, _tts_start
    _stop_flag.set()
    with _sentence_queue.mutex:
        _sentence_queue.queue.clear()
    with _audio_queue.mutex:
        while _audio_queue.queue:
            path, _, _ = _audio_queue.queue.popleft()
            if os.path.exists(path):
                os.remove(path)
    _tts_envelope = None
    _tts_start = None
    if _play_process and _play_process.poll() is None:
        _play_process.terminate()