import json
import os
import time
import uuid
import requests
from config import MEMORY_LOG, OLLAMA_URL, LLM_MODEL

EXTRACTION_PROMPT = (
    "Extract durable facts about the user from this conversation that would be "
    "useful to remember in future sessions (preferences, ongoing projects, names, "
    "decisions, etc). Ignore small talk. Return each fact as a complete, "
    "self-contained sentence (e.g. 'The user's name is Vello' not just 'Vello'), "
    "one per line, no numbering. If nothing is worth remembering, return NOTHING.\n\n"
    "Conversation:\n{transcript}"
)

def load_memory():
    if not os.path.exists(MEMORY_LOG):
        return []
    try:
        with open(MEMORY_LOG) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

def _save_memory(entries):
    with open(MEMORY_LOG, "w") as f:
        json.dump(entries, f, indent=2)

def add_facts(facts, source=None):
    entries = load_memory()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for fact in facts:
        entries.append({
            "id": str(uuid.uuid4()),
            "text": fact,
            "timestamp": now,
            "source": source,
            "embedding": None,
        })
    _save_memory(entries)

def summarize_and_store(conversation_entries, source=None, timeout=30):
    if not conversation_entries:
        print("[memory] no conversation entries, skipping")
        return
    transcript = "\n".join(f"{e['speaker']}: {e['text']}" for e in conversation_entries)
    prompt = EXTRACTION_PROMPT.format(transcript=transcript)
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False},
            timeout=timeout,
        )
        resp.raise_for_status()
        reply = resp.json()["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        print(f"[memory] extraction request failed: {e}")
        return

    print(f"[memory] raw extraction reply: {reply!r}")
    if not reply or reply.upper() == "NOTHING":
        print("[memory] nothing worth storing")
        return
    facts = [line.strip("-• ").strip() for line in reply.splitlines() if line.strip()]
    add_facts(facts, source=source)
    print(f"[memory] stored {len(facts)} fact(s)")

def get_memory_context(limit=None):
    entries = load_memory()
    if limit:
        entries = entries[-limit:]
    if not entries:
        return ""
    facts = "\n".join(f"- {e['text']}" for e in entries)
    return f"Known context about the user from past conversations:\n{facts}"