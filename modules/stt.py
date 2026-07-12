import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from scipy.signal import resample_poly
import subprocess
import threading
from config import SAMPLE_RATE, WHISPER_BIN, WHISPER_MODEL

_frames = []
_stream = None
_stream_ready = threading.Event()
_level = 0.0
_device = None  # None = system default
_actual_rate = SAMPLE_RATE

print("### STT MODULE LOADED — TEST MARKER ###")

def _callback(indata, frame_count, time_info, status):
    global _level
    if status:
        print(f"[stt] callback status flag: {status}")
    _frames.append(indata.copy())
    rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
    _level = min(rms / 4000, 1.0)
    print(f"[stt] callback fired, frame_count={frame_count}, rms={rms:.1f}")

def list_devices():
    """Returns [(index, name), ...] for input-capable devices."""
    return [(i, d["name"]) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]

def set_device(index):
    global _device
    _device = index

def get_device():
    """Returns (index, name) of the device currently selected (or system default)."""
    if _device is not None:
        return _device, sd.query_devices(_device)["name"]
    idx = sd.default.device[0]
    return idx, sd.query_devices(idx)["name"]

def get_level():
    return _level

def is_active():
    return _stream is not None

def start_recording():
    global _stream, _frames, _actual_rate
    print("[stt] start_recording() called")
    if _stream is not None:
        try:
            _stream.stop()
            _stream.close()
        except Exception:
            pass
    _stream_ready.clear()
    _frames = []
    try:
        _stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                  device=_device, callback=_callback)
        _actual_rate = SAMPLE_RATE
        print(f"[stt] opened at {SAMPLE_RATE}, device={_device}")
    except Exception as e:
        print(f"[stt] primary open failed: {e}")
        native_rate = int(sd.query_devices(_device)["default_samplerate"])
        _stream = sd.InputStream(samplerate=native_rate, channels=1, dtype="int16",
                                  device=_device, callback=_callback)
        _actual_rate = native_rate
        print(f"[stt] opened at fallback rate {native_rate}, device={_device}")
    _stream.start()
    print("[stt] stream.start() succeeded")
    _stream_ready.set()

def stop_recording(filename="input.wav"):
    global _stream
    print(f"[stt] stop_recording() called, _stream is None: {_stream is None}")
    ready = _stream_ready.wait(timeout=5)
    print(f"[stt] _stream_ready.wait() returned: {ready}, _stream is None: {_stream is None}")
    if _stream is None:
        return None
    _stream.stop()
    _stream.close()
    _stream = None
    print(f"[stt] total frames captured: {len(_frames)}")
    if not _frames:
        return None
    audio = np.concatenate(_frames, axis=0)
    if _actual_rate != SAMPLE_RATE:
        audio = resample_poly(audio, SAMPLE_RATE, _actual_rate).astype(np.int16)
    write(filename, SAMPLE_RATE, audio)
    return filename

def transcribe(filename="input.wav"):
    subprocess.run(
        [WHISPER_BIN, "-m", WHISPER_MODEL, "-f", filename, "-nt", "-otxt"],
        capture_output=True, text=True
    )
    with open(f"{filename}.txt") as f:
        return f.read().strip()