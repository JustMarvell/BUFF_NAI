import tkinter as tk
import threading
from modules.stt import start_recording, stop_recording, transcribe
from modules.llm import ask_stream, reset_history
from modules.tts import start_worker, begin_session, queue_sentence, wait_until_done, stop_speaking
from modules.ollama_ctl import start_ollama, stop_ollama, restart_ollama

def on_press(event):
    set_button(bg="#e74c3c", text="Recording...")
    set_status("Recording...")
    threading.Thread(target=_begin_recording, daemon=True).start()
    
def _begin_recording():
    stop_speaking()
    start_recording()

def on_release(event):
    talk_button.config(bg="#f1c40f", text="Processing...", state="disabled")
    status_label.config(text="Processing...")
    threading.Thread(target=process_audio, daemon=True).start()

def process_audio():
    filename = stop_recording()
    if not filename:
        set_status("Nothing recorded, try again.")
        reset_button()
        return

    text = transcribe(filename)
    if not text:
        set_status("Nothing transcribed, try again.")
        reset_button()
        return

    set_status(f"You said: {text}")
    set_button(bg="#3498db", text="Speaking...")
    begin_session()

    reply_parts = []
    def on_sentence(sentence):
        reply_parts.append(sentence)
        queue_sentence(sentence)
        set_status(f"AI: {' '.join(reply_parts)}")

    try:
        ask_stream(text, on_sentence)
    except ConnectionError as e:
        set_status(f"{e}\nIs Ollama running?")
        reset_button()
        return

    wait_until_done()
    reset_button()

def reset_button():
    set_button(bg=DEFAULT_BG, text="Hold to Talk", state="normal")
    
def on_new_conversation():
    reset_history()
    status_label.config(text="New conversation started.")
    
def on_stop_speaking():
    threading.Thread(target=_stop_speaking_thread, daemon=True).start()
    
def _stop_speaking_thread():
    stop_speaking()
    set_status("Playback stopped.")
    
def on_ollama_control(action_func, label):
    set_status(f"Ollama: {label}ing...")
    threading.Thread(target=_ollama_control_thread, args=(action_func, label), daemon=True).start()

def _ollama_control_thread(action_func, label):
    try:
        action_func()
        set_status(f"Ollama: {label} succeeded.")
    except RuntimeError as e:
        set_status(f"Ollama {label} failed: {e}")
        
def set_status(text):
    root.after(0, lambda: status_label.config(text=text))
    
def set_button(bg=None, text=None, state=None):
    def _update():
        if bg is not None:
            talk_button.config(bg=bg)
        if text is not None:
            talk_button.config(text=text)
        if state is not None:
            talk_button.config(state=state)
    root.after(0, _update)

root = tk.Tk()
root.title("BUFF_NAI")
root.geometry("500x400")

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