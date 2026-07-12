import requests
import json
import re
from config import OLLAMA_URL, LLM_MODEL, SYSTEM_PROMPT

history = [{"role": "system", "content": SYSTEM_PROMPT}]
SENTENCE_END = re.compile(r'(?<=[.!?])\s+')

def ask_stream(prompt, on_sentence, timeout=30):
    """Streams the LLM reply, calling on_sentence(text) as each sentence completes."""
    history.append({"role": "user", "content": prompt})
    buffer = ""
    full_reply = ""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": LLM_MODEL, "messages": history, "stream": True},
            stream=True, timeout=timeout
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            token = chunk.get("message", {}).get("content", "")
            buffer += token
            full_reply += token

            parts = SENTENCE_END.split(buffer)
            if len(parts) > 1:
                for sentence in parts[:-1]:
                    if sentence.strip():
                        on_sentence(sentence.strip())
                buffer = parts[-1]

            if chunk.get("done"):
                break
    except requests.exceptions.RequestException as e:
        history.pop()
        raise ConnectionError(f"Could not reach Ollama: {e}")

    if buffer.strip():
        on_sentence(buffer.strip())

    history.append({"role": "assistant", "content": full_reply})
    return full_reply

def reset_history():
    global history
    history = [{"role": "system", "content": SYSTEM_PROMPT}]