import queue
import threading
from modules.llm import ask_stream

_queue = queue.Queue()
_worker_started = False

def submit(text, speaker, on_sentence, on_done, on_error=None):
    _queue.put((text, speaker, on_sentence, on_done, on_error))

def _worker():
    while True:
        text, speaker, on_sentence, on_done, on_error = _queue.get()
        try:
            full_reply = ask_stream(text, on_sentence)
            on_done(full_reply)
        except Exception as e:
            if on_error:
                on_error(e)
        _queue.task_done()

def start_worker():
    global _worker_started
    if not _worker_started:
        threading.Thread(target=_worker, daemon=True).start()
        _worker_started = True