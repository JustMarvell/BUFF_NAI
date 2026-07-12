import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import subprocess
import threading
from config import SAMPLE_RATE, WHISPER_BIN, WHISPER_MODEL

_frames = []
_stream = None
_stream_ready = threading.Event()

def _callback(indata, frame_count, time_info, status):
    _frames.append(indata.copy())

def start_recording():
    global _stream, _frames
    if _stream is not None:
        try:
            _stream.stop()
            _stream.close()
        except Exception:
            pass
    _stream_ready.clear()
    _frames = []
    _stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=_callback)
    _stream.start()
    _stream_ready.set()

def stop_recording(filename="input.wav"):
    global _stream
    _stream_ready.wait(timeout=5)
    if _stream is None:
        return None
    _stream.stop()
    _stream.close()
    _stream = None
    if not _frames:
        return None
    audio = np.concatenate(_frames, axis=0)
    write(filename, SAMPLE_RATE, audio)
    return filename

def transcribe(filename="input.wav"):
    subprocess.run(
        [WHISPER_BIN, "-m", WHISPER_MODEL, "-f", filename, "-nt", "-otxt"],
        capture_output=True, text=True
    )
    with open(f"{filename}.txt") as f:
        return f.read().strip()