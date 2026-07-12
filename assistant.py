import sounddevice as sd
from scipy.io.wavfile import write
import subprocess
import requests

SAMPLE_RATE = 16000
WHISPER_BIN = "/home/vellosaurus/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "/home/vellosaurus/whisper.cpp/models/ggml-base.en.bin"
PIPER_MODEL = "/home/vellosaurus/piper_voices/en_US-amy-medium.onnx"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b-instruct-q4_K_M"

history = [{"role": "system", "content": "You are a helpful, concise voice assistant."}]

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

def ask(prompt):
    history.append({"role": "user", "content": prompt})
    resp = requests.post(OLLAMA_URL, json={"model": MODEL, "messages": history, "stream": False})
    reply = resp.json()["message"]["content"]
    history.append({"role": "assistant", "content": reply})
    return reply

def speak(text, filename="output.wav"):
    subprocess.run(
        ["piper", "--model", PIPER_MODEL, "--output_file", filename],
        input=text, text=True, capture_output=True
    )
    subprocess.run(["aplay", filename])

if __name__ == "__main__":
    while True:
        input("Press Enter to record (Ctrl+C to quit)...")
        record_audio(duration=5)
        text = transcribe()
        print("You said:", text)
        if not text:
            print("(nothing transcribed, try again)")
            continue
        reply = ask(text)
        print("AI:", reply)
        speak(reply)