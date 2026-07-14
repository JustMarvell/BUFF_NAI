import json
import os
import time
import zipfile
from config import CONVERSATION_LOG, LOG_DIR
from modules.memory import summarize_and_store

os.makedirs(LOG_DIR, exist_ok=True)

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

def archive_conversation():
    """Compresses the current log into logs/<date>_<time>_log.zip, then clears it.
    No-op if there's nothing to archive."""
    entries = load_conversation()
    if not entries:
        return None

    name = time.strftime("%Y%m%d_%H%M%S_log")
    archive_path = os.path.join(LOG_DIR, f"{name}.zip")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{name}.json", json.dumps(entries, indent=2))

    summarize_and_store(entries, source=name)
    clear_conversation()
    return archive_path