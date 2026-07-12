import requests

MODEL = "qwen2.5:7b-instruct-q4_K_M"
URL = "http://localhost:11434/api/chat"
history = [{"role": "system", "content": "You are a helpful, concise voice assistant."}]

def ask(prompt):
    history.append({"role": "user", "content": prompt})
    resp = requests.post(URL, json={"model": MODEL, "messages": history, "stream": False})
    reply = resp.json()["message"]["content"]
    history.append({"role": "assistant", "content": reply})
    return reply

while True:
    user_input = input("You: ")
    if user_input.lower() in ("exit", "quit"):
        break
    print("AI:", ask(user_input))