# BUFF_NAI

A fully local, offline AI TTS.

### Stages (project-level roadmap)
Stage 1 — Push-to-talk — [x] Complete
- The core loop: hold a button in a GUI window, speak, get transcribed, get a reply from a local LLM, hear it spoken back. Fully local, no cloud.

Stage 1.5 — Memory & persistence — [x] Complete
- Conversations are logged, archived, and summarized into long-term memory (via embeddings) so NAI can recall facts about the user across sessions.

Stage 2 — Hands-free / wake-word mode — Exploratory testing started
- Always-listening mode instead of holding a button. Requires voice activity detection (VAD) so the assistant knows when user is speaking without a manual trigger. Initial wake-word detection tested standalone via openWakeWord (sandbox/test_phrase_test.py), not yet integrated into the main pipeline.

Stage 3 — Sprite/avatar layer — Not started, optional/exploratory
- A visual character (PNG or sprite) that reacts to the conversation — e.g., changes expression based on sentiment or conversation state.

### Phases (the build steps so far)
| Phase | What it was | Status |
| --- | --- | --- |
| Phase 1 | Local LLM running via Ollama, basic terminal chat test | Done |
| Phase 2 | Speech-to-text via whisper.cpp, mic recording test | Done |
| Phase 3 | Text-to-speech via Piper, voice output test | Done |
| Phase 4 | Merged mic → LLM → voice into one working loop, converted to a GUI push-to-talk button (after the Wayland/pynput/evdev detour) | Done |
| Phase 5 | Polish: visual recording states, error handling for offline services, conversation reset, stop-speaking control, Ollama service controls | Done |
| Phase 6 | Streaming pipeline: LLM replies stream sentence-by-sentence straight into TTS instead of waiting for the full reply; live mic/TTS level meters and waveform display; mic device selector; text-input fallback alongside voice | Done |
| Phase 7 | Conversation persistence: sessions are logged to JSON, restored on launch, and archived to zip on reset/close; archived conversations are summarized by the LLM into durable facts, embedded, and stored as long-term memory, retrieved by similarity to enrich future replies | Done |
| Phase 8 | Discord bot integration: join/leave voice channel commands, mention-triggered text replies with TTS spoken into the voice channel; GUI and Discord requests now share a single serialized request queue (modules/request_queue.py) instead of the GUI calling the LLM directly | Done |

## Current Stage

## Current Stage

**Stage 1.5: Memory & persistence — Complete**
**Stage 2: Hands-free / wake-word mode — Exploratory testing only**

The full pipeline (mic → speech-to-text → LLM → text-to-speech) runs end-to-end through a GUI, with either push-to-talk or typed text input, and now also through a Discord bot (mention NAI in a text channel, or `/join` a voice channel to hear replies spoken aloud). Both interfaces submit requests through a shared queue so they don't collide. Replies stream sentence-by-sentence so TTS starts speaking before the LLM finishes generating. Conversations persist across sessions: the current session is logged and restored on launch, and past sessions are archived and mined for durable facts that get embedded and recalled automatically in later conversations.

A standalone openWakeWord test exists for wake-word detection, but it isn't wired into the main assistant yet. Not yet implemented: hands-free mode in the main app and the optional sprite/avatar layer.

## How It Works

1. **STT** — [whisper.cpp](https://github.com/ggerganov/whisper.cpp) transcribes recorded audio to text, running fully on CPU. Mic input device is selectable in the GUI, with automatic sample-rate fallback per device.
2. **LLM** — [Ollama](https://ollama.com) serves a local quantized model (default: Qwen2.5 7B Instruct) over a local HTTP API, streaming the reply token-by-token and maintaining conversation history.
3. **TTS** — [Piper](https://github.com/rhasspy/piper) synthesizes each completed sentence as it streams in and plays it back, so audio starts before the full reply is ready.
4. **Discord** — A bot (`discord.py`) mirrors the same LLM pipeline: mentioning the bot in a text channel gets a text reply, and `/join`ing a voice channel makes it speak replies aloud via Piper. Both GUI and Discord requests go through a shared queue (`modules/request_queue.py`) so only one LLM call runs at a time.
5. **Memory** — Each session is logged to disk and restored on next launch. On "New Conversation" or app close, the session is archived (zipped) and summarized by the LLM into standalone facts, which are embedded (via `nomic-embed-text`) and stored. Future prompts are matched against stored facts by cosine similarity and injected as context, giving NAI recall of past conversations.

All processing runs locally on-device. Nothing leaves the machine.

## Requirements

**Hardware this was built/tested on:**
- CPU: AMD Ryzen 5 6600H
- GPU: AMD Radeon 660M (integrated, not used for acceleration — inference runs on CPU)
- RAM: 16 GB DDR5
- OS: Linux (Zorin OS)
- A Discord bot token (only needed if you want the Discord integration — see `.env.example`)

No dedicated GPU is required. A 7-8B quantized model comfortably fits in 16GB RAM alongside Whisper and Piper.

**Software:**
- Python 3.12+
- [Ollama](https://ollama.com) (installed as a systemd service)
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) (built from source, requires `cmake` + `build-essential`)
- [Piper](https://github.com/rhasspy/piper) (`piper-tts` pip package)
- `portaudio19-dev` (system library, required by `sounddevice`)
- `python3-tk` (Tkinter, for the GUI)

## Setup / Replication

### 1. Install Ollama and pull models
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama pull nomic-embed-text
```
This installs Ollama as a systemd service (`ollama.service`), running automatically in the background. `nomic-embed-text` is used for memory embeddings.

### 2. Build whisper.cpp
```bash
sudo apt update
sudo apt install -y cmake build-essential
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
sh ./models/download-ggml-model.sh base.en
make
```
The compiled binary will be at `whisper.cpp/build/bin/whisper-cli`.

### 3. Install Piper and download a voice
```bash
sudo apt install -y portaudio19-dev
pip install piper-tts

mkdir -p ~/piper_voices
cd ~/piper_voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json
```

### 4. Install GUI and Python dependencies
```bash
sudo apt install -y python3-tk
pip install -r requirements.txt
```

### 5. (Optional) Set up the Discord bot
Copy `.env.example` to `.env` and fill in your bot token:
```bash
cp .env.example .env
```
Enable "Message Content Intent" for the bot in the Discord Developer Portal, and invite it with `bot` + `applications.commands` scopes. Skip this step if you don't want Discord support — the app runs fine without a token, the bot thread just won't log in.

### 6. Configure paths
Edit `config.py` to match where you installed whisper.cpp and downloaded the Piper voice model on your machine.

### 7. (Optional) Enable in-app Ollama controls
The GUI includes Start/Stop/Restart buttons for the Ollama service, which need passwordless `sudo` for those specific commands only:
```bash
sudo visudo -f /etc/sudoers.d/ollama-control
```
Add (adjust the username and `systemctl` path to match your system — check with `which systemctl`):
```
<your_username> ALL=(ALL) NOPASSWD: /usr/bin/systemctl start ollama, /usr/bin/systemctl stop ollama, /usr/bin/systemctl restart ollama
```
Skip this step if you'd rather manage Ollama manually — the rest of the app works fine without it.

### 8. Run
```bash
python3 assistant.py
```
A GUI window opens. Hold the "Hold to Talk" button to record, release to send — or type into the text field and hit Send/Enter. The button changes color to reflect state (recording, processing, speaking), a waveform shows mic/TTS activity, and separate buttons let you start a new conversation (archiving the current one into memory), stop playback mid-reply, pick a mic device, or control the Ollama service.

## Project Structure

```
├── modules/
│   ├── stt.py                   # Recording, device selection, Whisper transcription
│   ├── llm.py                    # Ollama chat wrapper, streaming, conversation history
│   ├── tts.py                     # Piper streaming synthesis + playback control
│   ├── ollama_ctl.py               # Start/stop/restart the Ollama systemd service
│   ├── persistence.py               # Conversation logging, loading, archiving
│   ├── memory.py                     # Fact extraction, embeddings, similarity recall
│   ├── request_queue.py               # Shared serialized queue for GUI + Discord requests
│   └── discord_bot.py                  # Discord bot: join/leave VC, mention replies, TTS in VC
├── scripts/
│   └── backfill_embeddings.py     # One-off: embed any memory entries missing one
├── sandbox/                # Early standalone test scripts, kept for reference (includes openWakeWord test)
├── sprite/                  # Placeholder for future avatar/sprite phase
├── logs/                     # Conversation logs + archives (gitignored)
├── .env.example               # Template for DISCORD_BOT_TOKEN
└── requirements.txt
```

## Notes

- This is a hobby/learning project, developed incrementally on consumer laptop hardware, no training or fine-tuning is performed; it uses pre-trained open-weight models via inference only.
- Model choice (`qwen2.5:7b-instruct-q4_K_M`) can be swapped for a smaller model (e.g. 3B) in `config.py` if performance is a concern on lower-spec hardware.
- I'm just a college student and I'm doing this project as a hobby project on my summer break. I don't know if i will keep continuing this project or not, but I will keep working on this if i have the time and interest.
- I'm not really an expert on AI or LLM so don't expect anything more than a hobby project
- If you're reading this, then congratulation, you've found a random youtube link. try opening this : https://youtu.be/Ve2aib93Cs8?si=vtW9mMMcKIQNm_v8