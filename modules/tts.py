import sys
import os
import subprocess
import queue
import threading
from config import PIPER_MODEL

PIPER_BIN = os.path.join(os.path.dirname(sys.executable), "piper")
if not os.path.exists(PIPER_BIN):
    PIPER_BIN = "piper"  # fall back to PATH lookup

_play_process = None
_sentence_queue = queue.Queue()
_stop_flag = threading.Event()
_worker_started = False

def _speak_one(text, filename="output.wav", timeout=30):
    global _play_process
    result = subprocess.run(
        [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", filename],
        input=text, text=True, capture_output=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(f"Piper failed: {result.stderr.strip()}")
    if _stop_flag.is_set():
        return
    _play_process = subprocess.Popen(["aplay", filename])
    _play_process.wait(timeout=timeout)
    _play_process = None

def _worker():
    while True:
        text = _sentence_queue.get()
        if not _stop_flag.is_set():
            try:
                _speak_one(text)
            except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"TTS error: {e}")
        _sentence_queue.task_done()

def start_worker():
    """Call once at app startup — starts the persistent playback thread."""
    global _worker_started
    if not _worker_started:
        threading.Thread(target=_worker, daemon=True).start()
        _worker_started = True

def begin_session():
    """Call before queuing a new reply's sentences."""
    _stop_flag.clear()

def queue_sentence(text):
    _sentence_queue.put(text)

def wait_until_done():
    _sentence_queue.join()

def speak(text, filename="output.wav", timeout=30):
    """Non-streaming single-shot speak, kept for compatibility."""
    _speak_one(text, filename, timeout)

def stop_speaking():
    _stop_flag.set()
    with _sentence_queue.mutex:
        _sentence_queue.queue.clear()
    if _play_process and _play_process.poll() is None:
        _play_process.terminate()