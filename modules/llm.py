import requests
from config import OLLAMA_URL, LLM_MODEL, SYSTEM_PROMPT

history = [{"role": "system", "content": SYSTEM_PROMPT}]

def ask(prompt, timeout=30):
    history.append({"role": "user", "content": prompt})
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": LLM_MODEL, "messages": history, "stream": False},
            timeout=timeout
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        history.pop()
        raise ConnectionError(f"Could not reach Ollama: {e}")
    reply = resp.json()["message"]["content"]
    history.append({"role": "assistant", "content": reply})
    return reply