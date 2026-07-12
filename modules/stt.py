import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import subprocess
from config import SAMPLE_RATE, WHISPER_BIN, WHISPER_MODEL

_frames = []
_stream = None

def _callback(indata, frame_count, time_info, status):
    _frames.append(indata.copy())

def start_recording():
    global _stream, _frames
    _frames = []
    _stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=_callback)
    _stream.start()

def stop_recording(filename="input.wav"):
    global _stream
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