import subprocess
from config import PIPER_MODEL

_play_process = None

def speak(text, filename="output.wav", timeout=30):
    global _play_process
    try:
        result = subprocess.run(
            ["piper", "--model", PIPER_MODEL, "--output_file", filename],
            input=text, text=True, capture_output=True, timeout=timeout
        )
        if result.returncode != 0:
            raise RuntimeError(f"Piper failed: {result.stderr.strip()}")
        _play_process = subprocess.Popen(["aplay", filename])
        _play_process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("TTS timed out")
    except FileNotFoundError:
        raise RuntimeError("Piper or aplay not found — check installation")
    finally:
        _play_process = None

def stop_speaking():
    global _play_process
    if _play_process and _play_process.poll() is None:
        _play_process.terminate()