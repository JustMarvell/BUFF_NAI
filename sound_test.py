import sounddevice as sd
import numpy as np

print("Default input device index:", sd.default.device[0])
print()
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        print(i, d["name"], "| hostapi:", sd.query_hostapis(d["hostapi"])["name"],
              "| default samplerate:", d["default_samplerate"])

print("\nRecording 3 seconds, speak now...")
audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype="int16")
sd.wait()
print("Max amplitude:", np.abs(audio).max())
print("RMS:", np.sqrt(np.mean(audio.astype(np.float32) ** 2)))