import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from pynput import keyboard
import subprocess
from config import SAMPLE_RATE, WHISPER_BIN, WHISPER_MODEL

PTT_KEY = keyboard.Key.space

def record_ptt(filename="input.wav"):
    frames = []
    state = {"active": False}

    def callback(indata, frame_count, time_info, status):
        if state["active"]:
            frames.append(indata.copy())

    def on_press(key):
        if key == PTT_KEY and not state["active"]:
            state["active"] = True
            print("Recording... (release SPACE to stop)")

    def on_release(key):
        if key == PTT_KEY and state["active"]:
            state["active"] = False
            return False

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback):
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

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