import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import subprocess
import evdev
from evdev import ecodes
from config import SAMPLE_RATE, WHISPER_BIN, WHISPER_MODEL

def find_keyboard():
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        if ecodes.KEY_SPACE in dev.capabilities().get(ecodes.EV_KEY, []):
            return dev
    raise RuntimeError("No keyboard device found. Try running with sudo to test, or check `input` group membership.")

def record_ptt(filename="input.wav"):
    dev = find_keyboard()
    frames = []
    state = {"active": False}

    def callback(indata, frame_count, time_info, status):
        if state["active"]:
            frames.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback):
        for event in dev.read_loop():
            if event.type == ecodes.EV_KEY and event.code == ecodes.KEY_SPACE:
                if event.value == 1 and not state["active"]:
                    state["active"] = True
                    print("Recording... (release SPACE to stop)")
                elif event.value == 0 and state["active"]:
                    state["active"] = False
                    break

    if not frames:
        return None
    audio = np.concatenate(frames, axis=0)
    write(filename, SAMPLE_RATE, audio)
    return filename

def transcribe(filename="input.wav"):
    subprocess.run(
        [WHISPER_BIN, "-m", WHISPER_MODEL, "-f", filename, "-nt", "-otxt"],
        capture_output=True, text=True
    )
    with open(f"{filename}.txt") as f:
        return f.read().strip()