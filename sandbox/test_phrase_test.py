import sounddevice as sd
import numpy as np
from openwakeword.model import Model

oww = Model(wakeword_models=["test_phrase.onnx"], inference_framework="onnx")

def callback(indata, frames, time, status):
    audio = indata[:, 0].astype(np.int16)
    prediction = oww.predict(audio)
    score = prediction["test_phrase"]
    if score > 0.5:
        print(f"DETECTED (score={score:.2f})")

with sd.InputStream(samplerate=16000, channels=1, dtype="int16",
                     blocksize=1280, callback=callback):
    print("Listening... say 'test phrase', Ctrl+C to stop")
    while True:
        sd.sleep(1000)