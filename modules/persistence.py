import json
import os
import time
from config import CONVERSATION_LOG

def load_conversation():
    if not os.path.exists(CONVERSATION_LOG):
        return []
    try:
        with open(CONVERSATION_LOG) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

def append_entry(speaker, text):
    entries = load_conversation()
    entry = {"speaker": speaker, "text": text, "timestamp": time.strftime("%H:%M:%S")}
    entries.append(entry)
    with open(CONVERSATION_LOG, "w") as f:
        json.dump(entries, f, indent=2)
    return entry

def clear_conversation():
    with open(CONVERSATION_LOG, "w") as f:
        json.dump([], f)