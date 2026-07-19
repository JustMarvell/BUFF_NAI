import tkinter as tk
from tkinter import ttk
import threading
import time
from collections import deque
from modules import request_queue
from modules.discord_bot import start_bot
from modules.stt import (start_recording, stop_recording, transcribe,
                          list_devices, set_device, get_device, get_level, is_active)
from modules.llm import reset_history
from modules.tts import (start_worker, begin_session, queue_sentence, wait_until_done,
                          stop_speaking, is_speaking, get_tts_level)
from modules.ollama_ctl import start_ollama, stop_ollama, restart_ollama
from modules.persistence import load_conversation, append_entry, clear_conversation, archive_conversation
import modules.theme as t
from modules import handsfree

_handsfree_thread = None
_handsfree_active = False
_meter_after_id = None

def on_handsfree_toggle():
    global _handsfree_thread, _handsfree_active
    if _handsfree_active:
        handsfree.stop()
        _handsfree_active = False
        handsfree_button.config(text="Hands-Free: Off", bg=t.BG_INPUT)
        talk_button.config(state="normal")
    else:
        _handsfree_active = True
        handsfree_button.config(text="Hands-Free: On", bg=t.ACCENT_SOFT)
        talk_button.config(state="disabled")
        _handsfree_thread = threading.Thread(
            target=handsfree.run,
            kwargs={"on_status": set_status, "on_conversation": append_conversation},
            daemon=True
        )
        _handsfree_thread.start()

def on_press(event):
    set_button(bg=t.STATE_RECORDING, text="Recording...")
    set_status("Recording...")
    threading.Thread(target=_begin_recording, daemon=True).start()

def _begin_recording():
    stop_speaking()
    try:
        start_recording()
    except Exception as e:
        set_status(f"Mic error: {e}")
        set_button(bg=t.STATE_IDLE, text="Hold to Talk", state="normal")

def on_release(event):
    talk_button.config(bg=t.STATE_PROCESSING, text="Processing...", state="disabled")
    status_label.config(text="Processing...")
    threading.Thread(target=process_audio, daemon=True).start()

def process_text(text):
    user_entry = append_entry("user", text, source="gui")
    append_conversation(f"[{user_entry['timestamp']}] You: {text}\n", "user")
    set_status("Thinking...")
    begin_session()

    ai_started = False
    done_event = threading.Event()

    def on_sentence(sentence):
        nonlocal ai_started
        if not ai_started:
            append_conversation(f"[{time.strftime('%H:%M:%S')}] NAI: ", "ai")
            ai_started = True
        else:
            append_conversation(" ", "ai")
        append_conversation(sentence, "ai")
        queue_sentence(sentence)

    def on_done(full_reply):
        append_entry("ai", full_reply, source="gui")
        append_conversation("\n\n")
        done_event.set()

    def on_error(e):
        set_status(f"{e}\nIs Ollama running?")
        done_event.set()

    request_queue.submit(text, "gui", on_sentence, on_done, on_error)
    done_event.wait()
    set_status("Done.")
    wait_until_done()

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
    set_button(bg=t.STATE_SPEAKING, text="Speaking...")
    process_text(text)
    reset_button()

def on_text_submit(event=None):
    text = text_entry.get().strip()
    if not text:
        return
    text_entry.delete(0, "end")
    text_entry.config(state="disabled")
    send_button.config(state="disabled")
    threading.Thread(target=_text_submit_thread, args=(text,), daemon=True).start()

def _text_submit_thread(text):
    process_text(text)
    root.after(0, _reset_text_input)

def _reset_text_input():
    text_entry.config(state="normal")
    send_button.config(state="normal")
    text_entry.focus()

def reset_button():
    set_button(bg=t.STATE_IDLE, text="Hold to Talk", state="normal")

def on_new_conversation():
    archive_conversation()
    reset_history()
    conversation_text.config(state="normal")
    conversation_text.delete("1.0", "end")
    conversation_text.config(state="disabled")
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
            talk_button.config(bg=bg, activebackground=bg)
        if text is not None:
            talk_button.config(text=text)
        if state is not None:
            talk_button.config(state=state)
    root.after(0, _update)

def append_conversation(text, tag=None):
    def _update():
        conversation_text.config(state="normal")
        conversation_text.insert("end", text, tag)
        conversation_text.see("end")
        conversation_text.config(state="disabled")
    root.after(0, _update)

def draw_meter(level):
    width = int(280 * level)
    color = t.ACCENT if level < 0.7 else t.STATE_RECORDING
    meter_canvas.coords(meter_bar, 0, 0, width, 10)
    meter_canvas.itemconfig(meter_bar, fill=color)

WAVE_BARS = 32
_wave_history = deque([0.0] * WAVE_BARS, maxlen=WAVE_BARS)

def draw_waveform(speaking):
    wave_canvas.delete("bar")
    w, h = 280, 36
    bar_w = w / WAVE_BARS
    color = t.PINK if speaking else t.BG_INPUT
    for i, level in enumerate(_wave_history):
        bar_h = max(2, level * h)
        x0, x1 = i * bar_w + 1, (i + 1) * bar_w - 1
        y0 = (h - bar_h) / 2
        wave_canvas.create_rectangle(x0, y0, x1, y0 + bar_h, fill=color, width=0, tags="bar")

def update_meter():
    global _handsfree_active
    global _meter_after_id
    hf_running = handsfree.is_running()
    active = is_active() or hf_running
    level = handsfree.get_level() if hf_running else (get_level() if is_active() else 0.0)
    draw_meter(level)

    if _handsfree_active and _handsfree_thread is not None and not _handsfree_thread.is_alive():
        _handsfree_active = False
        handsfree_button.config(text="Hands-Free: Off", bg=t.BG_INPUT)
        talk_button.config(state="normal")

    idx, name = get_device()
    mic_status_label.config(text=f"Mic · {name} · {handsfree.get_state() if hf_running else ('listening' if active else 'idle')}")

    speaking = is_speaking()
    _wave_history.append(get_tts_level() if speaking else 0.0)
    draw_waveform(speaking)

    _meter_after_id = root.after(50, update_meter)

def on_close():
    if _meter_after_id is not None:
        root.after_cancel(_meter_after_id)
    archive_conversation()
    root.destroy()


root = tk.Tk()
root.title("BUFF_NAI")
root.geometry("520x820")
root.configure(bg=t.BG_MAIN)

style = ttk.Style()
style.theme_use("clam")
style.configure("TCombobox",
                 fieldbackground=t.BG_INPUT, background=t.BG_INPUT,
                 foreground=t.TEXT_PRIMARY, arrowcolor=t.ACCENT,
                 bordercolor=t.BG_PANEL, lightcolor=t.BG_INPUT, darkcolor=t.BG_INPUT)
style.map("TCombobox", fieldbackground=[("readonly", t.BG_INPUT)],
          selectbackground=[("readonly", t.BG_INPUT)],
          selectforeground=[("readonly", t.TEXT_PRIMARY)])

header_frame = tk.Frame(root, bg=t.BG_MAIN)
header_frame.pack(pady=(18, 6))
tk.Label(header_frame, text="BUFF_NAI", font=t.FONT_TITLE, bg=t.BG_MAIN, fg=t.ACCENT).pack()
tk.Label(header_frame, text="your local voice companion", font=t.FONT_SUBTITLE,
         bg=t.BG_MAIN, fg=t.TEXT_MUTED).pack()

ollama_frame = tk.Frame(root, bg=t.BG_MAIN)
ollama_frame.pack(pady=8)

def make_pill_button(parent, text, command, bg=t.BG_INPUT, fg=t.TEXT_PRIMARY, font=t.FONT_SMALL):
    btn = tk.Button(parent, text=text, command=command, font=font,
                     bg=bg, fg=fg, activebackground=t.ACCENT_SOFT, activeforeground=t.BG_MAIN,
                     relief="flat", bd=0, padx=10, pady=4, cursor="hand2")
    return btn

make_pill_button(ollama_frame, "Start Ollama", lambda: on_ollama_control(start_ollama, "start")).pack(side="left", padx=3)
make_pill_button(ollama_frame, "Stop Ollama", lambda: on_ollama_control(stop_ollama, "stop")).pack(side="left", padx=3)
make_pill_button(ollama_frame, "Restart Ollama", lambda: on_ollama_control(restart_ollama, "restart")).pack(side="left", padx=3)

talk_button = tk.Button(root, text="Hold to Talk", font=t.FONT_BUTTON, width=20, height=3,
                         bg=t.STATE_IDLE, fg=t.TEXT_PRIMARY, activebackground=t.STATE_IDLE,
                         activeforeground=t.TEXT_PRIMARY, relief="flat", bd=0, cursor="hand2")
DEFAULT_BG = t.STATE_IDLE
talk_button.bind("<ButtonPress-1>", on_press)
talk_button.bind("<ButtonRelease-1>", on_release)
talk_button.pack(pady=18)

meter_canvas = tk.Canvas(root, width=280, height=10, bg=t.BG_INPUT, highlightthickness=0)
meter_canvas.pack(pady=(0, 6))
meter_bar = meter_canvas.create_rectangle(0, 0, 0, 10, fill=t.ACCENT, width=0)

mic_status_label = tk.Label(root, text="Mic  ·  —", font=t.FONT_SMALL, bg=t.BG_MAIN, fg=t.TEXT_MUTED)
mic_status_label.pack()

wave_canvas = tk.Canvas(root, width=280, height=36, bg=t.BG_MAIN, highlightthickness=0)
wave_canvas.pack(pady=(10, 0))

_devices = list_devices()
_device_names = [name for _, name in _devices]
_device_indices = [idx for idx, _ in _devices]

device_var = tk.StringVar()

def on_device_change(event=None):
    selected = device_var.get()
    idx = _device_indices[_device_names.index(selected)]
    set_device(idx)

device_menu = ttk.Combobox(root, textvariable=device_var, values=_device_names,
                            state="readonly", width=38, style="TCombobox")
if _device_names:
    default_idx, default_name = get_device()
    device_var.set(default_name if default_name in _device_names else _device_names[0])
device_menu.pack(pady=8)
device_menu.bind("<<ComboboxSelected>>", on_device_change)

controls_frame = tk.Frame(root, bg=t.BG_MAIN)
controls_frame.pack(pady=4)
make_pill_button(controls_frame, "Stop Speaking", on_stop_speaking, bg=t.BG_INPUT, font=t.FONT_BODY).pack(side="left", padx=4)
make_pill_button(controls_frame, "New Conversation", on_new_conversation, bg=t.BG_INPUT, font=t.FONT_BODY).pack(side="left", padx=4)

status_label = tk.Label(root, text="Hold the button to talk", wraplength=320, font=t.FONT_SMALL,
                         bg=t.BG_MAIN, fg=t.TEXT_MUTED, justify="center")
status_label.pack(pady=(6, 0))

handsfree_button = make_pill_button(controls_frame, "Hands-Free: Off", on_handsfree_toggle,
                                     bg=t.BG_INPUT, font=t.FONT_BODY)
handsfree_button.pack(side="left", padx=4)

conversation_frame = tk.Frame(root, bg=t.BG_PANEL, highlightbackground=t.BG_INPUT, highlightthickness=1)
conversation_frame.pack(pady=10, padx=16, fill="both", expand=True)

conversation_scroll = tk.Scrollbar(conversation_frame, bg=t.BG_PANEL, troughcolor=t.BG_MAIN,
                                    activebackground=t.ACCENT_SOFT, relief="flat", bd=0)
conversation_scroll.pack(side="right", fill="y")

conversation_text = tk.Text(conversation_frame, height=10, wrap="word",
                             yscrollcommand=conversation_scroll.set, state="disabled",
                             bg=t.BG_PANEL, fg=t.TEXT_PRIMARY, insertbackground=t.TEXT_PRIMARY,
                             selectbackground=t.ACCENT_SOFT, relief="flat", bd=0,
                             padx=10, pady=10, font=t.FONT_BODY)
conversation_text.pack(side="left", fill="both", expand=True)
conversation_scroll.config(command=conversation_text.yview)

conversation_text.tag_config("user", foreground=t.ACCENT)
conversation_text.tag_config("ai", foreground=t.PINK)

for entry in load_conversation():
    tag = "user" if entry["speaker"] == "user" else "ai"
    label = "You" if entry["speaker"] == "user" else "NAI"
    conversation_text.config(state="normal")
    conversation_text.insert("end", f"[{entry['timestamp']}] {label}: {entry['text']}\n\n", tag)
    conversation_text.config(state="disabled")
conversation_text.see("end")

input_frame = tk.Frame(root, bg=t.BG_MAIN)
input_frame.pack(pady=(0, 16), padx=16, fill="x")

text_entry = tk.Entry(input_frame, font=t.FONT_BODY, bg=t.BG_INPUT, fg=t.TEXT_PRIMARY,
                       insertbackground=t.TEXT_PRIMARY, relief="flat", bd=0,
                       highlightthickness=1, highlightbackground=t.BG_INPUT, highlightcolor=t.ACCENT)
text_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
text_entry.bind("<Return>", on_text_submit)

send_button = make_pill_button(input_frame, "Send", on_text_submit, bg=t.ACCENT_SOFT, fg=t.BG_MAIN, font=t.FONT_BODY)
send_button.pack(side="left")

root.protocol("WM_DELETE_WINDOW", on_close)

start_worker()
request_queue.start_worker()
start_bot()
update_meter()
root.mainloop()