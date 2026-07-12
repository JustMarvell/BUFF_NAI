import requests
from config import OLLAMA_URL, LLM_MODEL, SYSTEM_PROMPT

history = [{"role": "system", "content": SYSTEM_PROMPT}]

def ask(prompt):
    history.append({"role": "user", "content": prompt})
    resp = requests.post(OLLAMA_URL, json={"model": LLM_MODEL, "messages": history, "stream": False})
    reply = resp.json()["message"]["content"]
    history.append({"role": "assistant", "content": reply})
    return reply