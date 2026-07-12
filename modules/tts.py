import subprocess
import queue
import threading
import tempfile
import os
import sys
from config import PIPER_MODEL

PIPER_BIN = os.path.join(os.path.dirname(sys.executable), "piper")
if not os.path.exists(PIPER_BIN):
    PIPER_BIN = "piper"

_play_process = None
_sentence_queue = queue.Queue()
_audio_queue = queue.Queue()
_stop_flag = threading.Event()
_workers_started = False

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
                    _audio_queue.put(path)
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                print(f"TTS synth error: {e}")
        _sentence_queue.task_done()

def _play_worker():
    global _play_process
    while True:
        path = _audio_queue.get()
        if not _stop_flag.is_set():
            try:
                _play_process = subprocess.Popen(["aplay", path])
                _play_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
            finally:
                _play_process = None
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

def stop_speaking():
    _stop_flag.set()
    with _sentence_queue.mutex:
        _sentence_queue.queue.clear()
    with _audio_queue.mutex:
        while _audio_queue.queue:
            path = _audio_queue.queue.popleft()
            if os.path.exists(path):
                os.remove(path)
    if _play_process and _play_process.poll() is None:
        _play_process.terminate()