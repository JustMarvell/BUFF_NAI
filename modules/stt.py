import sounddevice as sd
from scipy.io.wavfile import write
import subprocess
from config import SAMPLE_RATE, WHISPER_BIN, WHISPER_MODEL

def record_audio(filename="input.wav", duration=5):
    print("Recording...")
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    write(filename, SAMPLE_RATE, audio)

def transcribe(filename="input.wav"):
    subprocess.run(
        [WHISPER_BIN, "-m", WHISPER_MODEL, "-f", filename, "-nt", "-otxt"],
        capture_output=True, text=True
    )
    with open(f"{filename}.txt") as f:
        return f.read().strip()