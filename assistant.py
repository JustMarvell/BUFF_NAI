from modules.stt import record_ptt, transcribe
from modules.llm import ask
from modules.tts import speak

if __name__ == "__main__":
    print("Hold SPACE to talk. Ctrl+C to quit.")
    while True:
        record_ptt()
        text = transcribe()
        print("You said:", text)
        if not text:
            print("(nothing transcribed, try again)")
            continue
        reply = ask(text)
        print("AI:", reply)
        speak(reply)