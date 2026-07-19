import os
from dotenv import load_dotenv
load_dotenv()

SAMPLE_RATE = 16000

WHISPER_BIN = "/home/vellosaurus/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "/home/vellosaurus/whisper.cpp/models/ggml-base.en.bin"

PIPER_MODEL = "/home/vellosaurus/piper_voices/en_US-amy-medium.onnx"

OLLAMA_URL = "http://localhost:11434/api/chat"
EMBED_URL = "http://localhost:11434/api/embeddings"
LLM_MODEL = "qwen2.5:7b-instruct-q4_K_M"
EMBED_MODEL = "nomic-embed-text"
SYSTEM_PROMPT = "You are a voice assistant designed by VelloSaurus. Your job is to become a friend and assistant, you have a calm and casual demeanor, but sometimes you can get a bit emotional. Your full name is BUFF_NAI, or NAI in short."

LOG_DIR = "logs"
CONVERSATION_LOG = os.path.join(LOG_DIR, "latest_conversation_log.json")
MEMORY_LOG = os.path.join(LOG_DIR, "memory.json")

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

WAKEWORD_MODELS = [
    "models/wakeword/Hey_Nai/Hey_Nai.onnx",
    "models/wakeword/Hey_Buff_nai/Hey_Buff_nai.onnx",
    "models/wakeword/Hey_naaiy/Hey_naaiy.onnx",
]
VAD_AGGRESSIVENESS = 2
SILENCE_TIMEOUT = 1.2
FOLLOWUP_TIMEOUT = 8