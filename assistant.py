import tkinter as tk
from tkinter import ttk
from modules.stt import (start_recording, stop_recording, transcribe,
                          list_devices, set_device, get_device, get_level, is_active)
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
    try:
        start_recording()
    except Exception as e:
        set_status(f"Mic error: {e}")
        set_button(bg=DEFAULT_BG, text="Hold to Talk", state="normal")

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
    
def draw_meter(level):
    width = int(280 * level)
    color = "#2ecc71" if level < 0.7 else "#e74c3c"
    meter_canvas.coords(meter_bar, 0, 0, width, 16)
    meter_canvas.itemconfig(meter_bar, fill=color)

def update_meter():
    active = is_active()
    draw_meter(get_level() if active else 0.0)
    idx, name = get_device()
    mic_status_label.config(text=f"Mic: {name} ({'Active' if active else 'Idle'})")
    root.after(50, update_meter)

root = tk.Tk()
root.title("BUFF_NAI")
root.geometry("500x400")

ollama_frame = tk.Frame(root)
ollama_frame.pack(pady=5)

talk_button = tk.Button(root, text="Hold to Talk", font=("Arial", 14), width=20, height=3)

meter_canvas = tk.Canvas(root, width=280, height=16, bg="#222", highlightthickness=0)
meter_canvas.pack(pady=(0, 5))
meter_bar = meter_canvas.create_rectangle(0, 0, 0, 16, fill="#2ecc71", width=0)

mic_status_label = tk.Label(root, text="Mic: —")
mic_status_label.pack()

_devices = list_devices()
_device_names = [name for _, name in _devices]
_device_indices = [idx for idx, _ in _devices]

device_var = tk.StringVar()

def on_device_change(event=None):
    selected = device_var.get()
    idx = _device_indices[_device_names.index(selected)]
    set_device(idx)

device_menu = ttk.Combobox(root, textvariable=device_var, values=_device_names,
                            state="readonly", width=38)
if _device_names:
    default_idx, default_name = get_device()
    device_var.set(default_name if default_name in _device_names else _device_names[0])
device_menu.pack(pady=5)
device_menu.bind("<<ComboboxSelected>>", on_device_change)

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

update_meter()
root.mainloop()
root.mainloop()