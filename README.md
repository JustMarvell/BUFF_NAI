# BUFF_NAI

A fully local, offline AI TTS.

### Stages (project-level roadmap)
Stage 1 — Push-to-talk — [x] Complete
- The core loop: hold a button in a GUI window, speak, get transcribed, get a reply from a local LLM, hear it spoken back. Fully local, no cloud.

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
| Phase 5 | Polish: visual recording states, error handling for offline services, conversation reset, stop-speaking control, Ollama service controls | Done |

### Roadmap
- [x] Local LLM running via Ollama
- [x] Speech-to-text via whisper.cpp
- [x] Text-to-speech via Piper
- [x] Merged mic → LLM → voice loop (fixed 5s recording window)
- [x] True push-to-talk via GUI button (global hotkeys blocked on Wayland, switched to a Tkinter hold-button instead)
- [x] Stage 1 polish (status colors, error handling, conversation reset, stop-speaking, Ollama controls)
- [ ] Hands-free / wake-word mode (voice activity detection)
- [ ] Sprite/avatar reacting to conversation (optional, exploratory)

## Current Stage

**Stage 1: Push-to-talk — Complete**

The full pipeline (mic → speech-to-text → LLM → text-to-speech) runs end-to-end through a GUI push-to-talk button. True global-hotkey push-to-talk was attempted first (`pynput`, then `evdev`) but blocked by Wayland's input restrictions; a Tkinter GUI button sidesteps this cleanly and works identically on X11 or Wayland. Stage 1 also includes polish: a color-coded button (idle / recording / processing / speaking), friendly error handling if Ollama or Piper aren't reachable, a conversation reset button, a stop-speaking button, and start/stop/restart controls for the Ollama service.

Not yet implemented: hands-free/wake-word mode and the optional sprite/avatar layer.

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
- [Ollama](https://ollama.com) (installed as a systemd service)
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) (built from source, requires `cmake` + `build-essential`)
- [Piper](https://github.com/rhasspy/piper) (`piper-tts` pip package)
- `portaudio19-dev` (system library, required by `sounddevice`)
- `python3-tk` (Tkinter, for the GUI)

## Setup / Replication

### 1. Install Ollama and pull a model
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b-instruct-q4_K_M
```
This installs Ollama as a systemd service (`ollama.service`), running automatically in the background.

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

### 5. Configure paths
Edit `config.py` to match where you installed whisper.cpp and downloaded the Piper voice model on your machine.

### 6. (Optional) Enable in-app Ollama controls
The GUI includes Start/Stop/Restart buttons for the Ollama service, which need passwordless `sudo` for those specific commands only:
```bash
sudo visudo -f /etc/sudoers.d/ollama-control
```
Add (adjust the username and `systemctl` path to match your system — check with `which systemctl`):
```
<your_username> ALL=(ALL) NOPASSWD: /usr/bin/systemctl start ollama, /usr/bin/systemctl stop ollama, /usr/bin/systemctl restart ollama
```
Skip this step if you'd rather manage Ollama manually — the rest of the app works fine without it.

### 7. Run
```bash
python3 assistant.py
```
A GUI window opens. Hold the "Hold to Talk" button to record, release to send. The button changes color to reflect state (recording, processing, speaking), and separate buttons let you start a new conversation, stop playback mid-reply, or control the Ollama service.

## Project Structure

```
BUFF_NAI/
├── assistant.py         # Main entry point — GUI, wires modules together
├── config.py              # All paths and model constants
├── modules/
│   ├── stt.py               # Recording + Whisper transcription
│   ├── llm.py                # Ollama chat wrapper + conversation history
│   ├── tts.py                 # Piper speech synthesis + playback control
│   └── ollama_ctl.py            # Start/stop/restart the Ollama systemd service
├── sandbox/               # Early standalone test scripts, kept for reference
├── sprite/                # Placeholder for future avatar/sprite phase
└── requirements.txt
```

## Notes

- This is a hobby/learning project, developed incrementally on consumer laptop hardware, no training or fine-tuning is performed; it uses pre-trained open-weight models via inference only.
- Model choice (`qwen2.5:7b-instruct-q4_K_M`) can be swapped for a smaller model (e.g. 3B) in `config.py` if performance is a concern on lower-spec hardware.
- I'm just a college student and I'm doing this project as a hobby project on my summer break. I don't know if i will keep continuing this project or not, but I will keep working on this if i have the time and interest.
- I'm not really an expert on AI or LLM so don't expect anything more than a hobby project
- If you're reading this, then congratulation, you've found a random youtube link. try opening this : https://youtu.be/Ve2aib93Cs8?si=vtW9mMMcKIQNm_v8