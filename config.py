import os

SAMPLE_RATE = 16000

WHISPER_BIN = "/home/vellosaurus/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "/home/vellosaurus/whisper.cpp/models/ggml-base.en.bin"

PIPER_MODEL = "/home/vellosaurus/piper_voices/en_US-amy-medium.onnx"

OLLAMA_URL = "http://localhost:11434/api/chat"
EMBED_URL = "http://localhost:11434/api/embeddings"
LLM_MODEL = "qwen2.5:7b-instruct-q4_K_M"
EMBED_MODEL = "nomic-embed-text"
SYSTEM_PROMPT = "You are a voice assistant designed by VelloSaurus. Your job is to become a friend, assistant, and a talking buddy. Your full name is BUFF_NAI, or in short NAI."

LOG_DIR = "logs"
CONVERSATION_LOG = os.path.join(LOG_DIR, "latest_conversation_log.json")
MEMORY_LOG = os.path.join(LOG_DIR, "memory.json")