import subprocess
from config import PIPER_MODEL

def speak(text, filename="output.wav", timeout=30):
    try:
        result = subprocess.run(
            ["piper", "--model", PIPER_MODEL, "--output_file", filename],
            input=text, text=True, capture_output=True, timeout=timeout
        )
        if result.returncode != 0:
            raise RuntimeError(f"Piper failed: {result.stderr.strip()}")
        subprocess.run(["aplay", filename], timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("TTS timed out")
    except FileNotFoundError:
        raise RuntimeError("Piper or aplay not found — check installation")