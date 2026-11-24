
import sounddevice as sd
import speech_recognition as sr
import soundfile as sf
import numpy as np
import io

print("DEX microphone test started.")

duration = 5
sample_rate = 16000

print("Speak now...")

audio_data = sd.rec(
    int(duration * sample_rate),
    samplerate=sample_rate,
    channels=1,
    dtype="int16"
)

sd.wait()

print("Recording completed!")

# Convert recorded audio into SpeechRecognition format
audio = sr.AudioData(
    audio_data.tobytes(),
    sample_rate,
    2
)

# Use SoundFile instead of the incompatible FLAC executable
def encode_flac(convert_rate=None, convert_width=None):
    samples = np.frombuffer(audio.frame_data, dtype="<i2")

    buffer = io.BytesIO()

    sf.write(
        buffer,
        samples,
        samplerate=sample_rate,
        format="FLAC",
        subtype="PCM_16"
    )

    return buffer.getvalue()

audio.get_flac_data = encode_flac

recognizer = sr.Recognizer()

try:
    print("Converting speech into text...")

    text = recognizer.recognize_google(audio)

    print("You said:", text)

except sr.UnknownValueError:
    print("Sorry, I couldn't understand your voice.")

except sr.RequestError as e:
    print("Speech recognition service error:", e)

except Exception as e:
    print("Error:", e)
