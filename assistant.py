import tkinter as tk
import threading
from modules.stt import start_recording, stop_recording, transcribe
from modules.llm import ask_stream, reset_history
from modules.tts import speak, stop_speaking, start_worker, begin_session, queue_sentence, wait_until_done, stop_speaking
from modules.ollama_ctl import start_ollama, stop_ollama, restart_ollama

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
        status_label.config(text="Nothing recorded, try again.")
        reset_button()
        return

    text = transcribe(filename)
    if not text:
        status_label.config(text="Nothing transcribed, try again.")
        reset_button()
        return

    status_label.config(text=f"You said: {text}")
    talk_button.config(bg="#3498db", text="Speaking...")
    begin_session()

    reply_parts = []
    def on_sentence(sentence):
        reply_parts.append(sentence)
        queue_sentence(sentence)
        status_label.config(text=f"AI: {' '.join(reply_parts)}")

    try:
        ask_stream(text, on_sentence)
    except ConnectionError as e:
        status_label.config(text=f"{e}\nIs Ollama running?")
        reset_button()
        return

    wait_until_done()
    reset_button()

def reset_button():
    talk_button.config(bg=DEFAULT_BG, text="Hold to Talk", state="normal")
    
def on_new_conversation():
    reset_history()
    status_label.config(text="New conversation started.")
    
def on_stop_speaking():
    stop_speaking()
    status_label.config(text="Playback stopped.")
    
def on_ollama_control(action_func, label):
    try:
        action_func()
        status_label.config(text=f"Ollama: {label} succeeded.")
    except RuntimeError as e:
        status_label.config(text=f"Ollama {label} failed: {e}")

root = tk.Tk()
root.title("BUFF_NAI")
root.geometry("500x200")

ollama_frame = tk.Frame(root)
ollama_frame.pack(pady=5)

talk_button = tk.Button(root, text="Hold to Talk", font=("Arial", 14), width=20, height=3)
DEFAULT_BG = talk_button.cget("bg")
talk_button.bind("<ButtonPress-1>", on_press)
talk_button.bind("<ButtonRelease-1>", on_release)
talk_button.pack(pady=20)

stop_button = tk.Button(root, text="Stop Speaking", font=("Arial", 10), command=on_stop_speaking)
stop_button.pack(pady=5)

new_conv_button = tk.Button(root, text="New Conversation", font=("Arial", 10), command=on_new_conversation)
new_conv_button.pack(pady=5)

tk.Button(ollama_frame, text="Start Ollama", font=("Arial", 9),
          command=lambda: on_ollama_control(start_ollama, "start")).pack(side="left", padx=2)
tk.Button(ollama_frame, text="Stop Ollama", font=("Arial", 9),
          command=lambda: on_ollama_control(stop_ollama, "stop")).pack(side="left", padx=2)
tk.Button(ollama_frame, text="Restart Ollama", font=("Arial", 9),
          command=lambda: on_ollama_control(restart_ollama, "restart")).pack(side="left", padx=2)

status_label = tk.Label(root, text="Hold the button to talk", wraplength=280)
status_label.pack()

start_worker()

root.mainloop()