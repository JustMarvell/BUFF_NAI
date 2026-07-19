import sounddevice as sd
import numpy as np
from openwakeword.model import Model

models = [
    "models/wakeword/Hey_Nai/Hey_Nai.onnx",
    "models/wakeword/Hey_Buff_nai/Hey_Buff_nai.onnx",
    "models/wakeword/Hey_naaiy/Hey_naaiy.onnx",
]
oww = Model(wakeword_models=models, inference_framework="onnx")

def callback(indata, frames, time, status):
    audio = indata[:, 0].astype(np.int16)
    prediction = oww.predict(audio)
    for name, score in prediction.items():
        if score > 0.5:
            print(f"DETECTED: {name} (score={score:.2f})")

with sd.InputStream(samplerate=16000, channels=1, dtype="int16",
                     blocksize=1280, callback=callback):
    print("Listening for all three phrases... Ctrl+C to stop")
    while True:
        sd.sleep(1000)