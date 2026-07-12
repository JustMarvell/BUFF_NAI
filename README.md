# BUFF_NAI

A fully local, offline AI Voice TTS.

### Stages (project-level roadmap)
Stage 1 — Push-to-talk - [v] Complete
- The core loop: hold a button, speak, get transcribed, get a reply from a local LLM, hear it spoken back. Fully local, no cloud.

Stage 2 — Hands-free / wake-word mode — Not started
- Always-listening mode instead of holding a button. Requires voice activity detection (VAD) so the assistant knows when you're speaking without a manual trigger.

Stage 3 — Sprite/avatar layer — Not started, optional/exploratory
- A visual character (PNG or sprite) that reacts to the conversation — e.g., changes expression based on sentiment or conversation state.

### Phases (the build steps that made up Stage 1)
| Phase | What it was | Status | 
| --- | --- | --- |
| Phase 1 | Local LLM running via Ollama, basic terminal chat test | Done | 
| Phase 2 | Speech-to-text via whisper.cpp, mic recording test | Done | 
| Phase 3 | Text-to-speech via Piper, voice output test | Done |
| Phase 4 | Merged mic → LLM → voice into one working loop, converted to a GUI push-to-talk button (after the Wayland/pynput/evdev detour) | Done |

### Roadmap
- [x] Local LLM running via Ollama
- [x] Speech-to-text via whisper.cpp
- [x] Text-to-speech via Piper
- [x] Merged mic → LLM → voice loop (fixed 5s recording window)
- [x] True push-to-talk (hold key to record, release to stop)
- [ ] Hands-free / wake-word mode (voice activity detection)
- [ ] Sprite/avatar reacting to conversation (optional, exploratory)

## Current Stage

**Stage 1: Push-to-talk — in progress**

The core pipeline (mic → speech-to-text → LLM → text-to-speech) is working end-to-end with a fixed-duration recording window. Not yet implemented: true push-to-talk (hold-to-record), hands-free/wake-word mode, and the optional sprite/avatar layer.

## How It Works

1. **STT** — [whisper.cpp](https://github.com/ggerganov/whisper.cpp) transcribes recorded audio to text, running fully on CPU.
2. **LLM** — [Ollama](https://ollama.com) serves a local quantized model (default: Qwen2.5 7B Instruct) over a local HTTP API, maintaining conversation history.
3. **TTS** — [Piper](https://github.com/rhasspy/piper) synthesizes the LLM's reply into speech and plays it back.

All three run locally on-device. Nothing leaves the machine.

## Requirements

**Hardware this was built/tested on:**
- CPU: AMD Ryzen 5 6600H
- GPU: AMD Radeon 660M (integrated, not used for acceleration — inference runs on CPU)
- RAM: 16 GB DDR5
- OS: Linux (Zorin OS)

No dedicated GPU is required. A 7-8B quantized model comfortably fits in 16GB RAM alongside Whisper and Piper.

**Software:**
- Python 3.12+
- [Ollama](https://ollama.com)
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) (built from source, requires `cmake` + `build-essential`)
- [Piper](https://github.com/rhasspy/piper) (`piper-tts` pip package)
- `portaudio19-dev` (system library, required by `sounddevice`)

## Setup / Replication

### 1. Install Ollama and pull a model
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b-instruct-q4_K_M
```

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

### 4. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure paths
Edit `config.py` to match where you installed whisper.cpp and downloaded the Piper voice model on your machine.

### 6. Run
```bash
python3 assistant.py
```
Press Enter to record (5 second window), speak, and the assistant will transcribe, respond, and speak back.

## Project Structure

```
BUFF_NAI/
├── assistant.py       # Main entry point — mic → STT → LLM → TTS loop
├── config.py           # All paths and model constants
├── modules/
│   ├── stt.py            # Recording + Whisper transcription
│   ├── llm.py             # Ollama chat wrapper + conversation history
│   └── tts.py              # Piper speech synthesis
├── sandbox/             # Early standalone test scripts, kept for reference
├── sprite/              # Placeholder for future avatar/sprite phase
└── requirements.txt
```

## Notes

- This is a hobby/learning project, developed incrementally on consumer laptop hardware, no training or fine-tuning is performed; it uses pre-trained open-weight models via inference only.
- Model choice (`qwen2.5:7b-instruct-q4_K_M`) can be swapped for a smaller model (e.g. 3B) in `config.py` if performance is a concern on lower-spec hardware.
- I'm just a college student and I'm doing this project as a hobby project on my summer break. I don't know if i will keep continuing this project or not, but I will keep working on this if i have the time and interest.
- I'm not really an expert on AI or LLM so don't expect anything more than a hobby project
- If you're reading this, then congratulation, you've found a random youtube link. try opening this : https://youtu.be/Ve2aib93Cs8?si=vtW9mMMcKIQNm_v8