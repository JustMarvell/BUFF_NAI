import subprocess
from config import PIPER_MODEL

def speak(text, filename="output.wav"):
    subprocess.run(
        ["piper", "--model", PIPER_MODEL, "--output_file", filename],
        input=text, text=True, capture_output=True
    )
    subprocess.run(["aplay", filename])