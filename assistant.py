from modules.stt import record_audio, transcribe
from modules.llm import ask
from modules.tts import speak

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