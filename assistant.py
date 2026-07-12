import tkinter as tk
import threading
from modules.stt import start_recording, stop_recording, transcribe
from modules.llm import ask
from modules.tts import speak

def on_press(event):
    talk_button.config(bg="#e74c3c", text="Recording...")
    status_label.config(text="Recording...")
    start_recording()

def on_release(event):
    talk_button.config(bg="#f1c40f", text="Processing...", state="disabled")
    status_label.config(text="Processing...")
    threading.Thread(target=process_audio, daemon=True).start()

def process_audio():
    filename = stop_recording()
    if not filename:
        status_label.config(text="No audio captured, try again.")
        reset_button()
        return

    text = transcribe(filename)
    if not text:
        status_label.config(text="Nothing transcribed, try again.")
        reset_button()
        return

    status_label.config(text=f"You said: {text}")

    try:
        reply = ask(text)
    except ConnectionError as e:
        status_label.config(text=f"{e}\nIs Ollama running?")
        reset_button()
        return

    status_label.config(text=f"AI: {reply}")

    try:
        speak(reply)
    except RuntimeError as e:
        status_label.config(text=f"AI: {reply}\n(voice error: {e})")

    reset_button()

def reset_button():
    talk_button.config(bg="SystemButtonFace", text="Hold to Talk", state="normal")

root = tk.Tk()
root.title("BUFF_NAI")
root.geometry("300x150")

talk_button = tk.Button(root, text="Hold to Talk", font=("Arial", 14), width=20, height=3)
talk_button.bind("<ButtonPress-1>", on_press)
talk_button.bind("<ButtonRelease-1>", on_release)
talk_button.pack(pady=20)

status_label = tk.Label(root, text="Hold the button to talk", wraplength=280)
status_label.pack()

root.mainloop()