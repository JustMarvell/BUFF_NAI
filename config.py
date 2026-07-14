import os

SAMPLE_RATE = 16000

WHISPER_BIN = "/home/vellosaurus/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "/home/vellosaurus/whisper.cpp/models/ggml-base.en.bin"

PIPER_MODEL = "/home/vellosaurus/piper_voices/en_US-amy-medium.onnx"

OLLAMA_URL = "http://localhost:11434/api/chat"
LLM_MODEL = "qwen2.5:7b-instruct-q4_K_M"
SYSTEM_PROMPT = "You are a helpful, concise voice assistant."

LOG_DIR = "logs"
CONVERSATION_LOG = os.path.join(LOG_DIR, "latest_conversation_log.json")
MEMORY_LOG = os.path.join(LOG_DIR, "memory.json")