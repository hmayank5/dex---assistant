
import time
import customtkinter as ctk
import speech_recognition as sr
import sounddevice as sd
import numpy as np
import soundfile as sf
import io
import threading
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai


# Load API key from the project's .env file
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)


# Configure appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DEXAssistant(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "Gemini API key not found. Check your .env file."
            )

        self.gemini_client = genai.Client(api_key=api_key)

        # Main window
        self.title("DEX - Desktop Assistant")
        self.geometry("800x600")
        self.minsize(650, 500)

        # Heading
        self.title_label = ctk.CTkLabel(
            self,
            text="DEX",
            font=("Arial", 42, "bold")
        )
        self.title_label.pack(pady=(35, 5))

        # Subtitle
        self.subtitle = ctk.CTkLabel(
            self,
            text="YOUR INTELLIGENT DESKTOP ASSISTANT",
            font=("Arial", 13)
        )
        self.subtitle.pack(pady=5)

        # Status
        self.status_label = ctk.CTkLabel(
            self,
            text="Status: Ready",
            font=("Arial", 14)
        )
        self.status_label.pack(pady=20)

        # Activate button
        self.mic_button = ctk.CTkButton(
            self,
            text="ACTIVATE DEX",
            width=200,
            height=55,
            font=("Arial", 16, "bold"),
            command=self.activate_assistant
        )
        self.mic_button.pack(pady=15)

        # Gesture sensor status
        self.gesture_label = ctk.CTkLabel(
            self,
            text="Gesture Sensor: Not Connected",
            font=("Arial", 13)
        )
        self.gesture_label.pack(pady=10)

        # Response box
        self.response_box = ctk.CTkTextbox(
            self,
            width=550,
            height=180,
            font=("Arial", 14)
        )
        self.response_box.pack(pady=20)

        self.show_message(
            "Hello! I am DEX.\n\n"
            "Your intelligent voice and gesture assistant.\n\n"
            "Waiting for your command..."
        )

    # Display messages
    def show_message(self, message):
        self.response_box.configure(state="normal")
        self.response_box.delete("0.0", "end")
        self.response_box.insert("0.0", message)
        self.response_box.configure(state="disabled")

    # Activate voice assistant
    def activate_assistant(self):
        self.mic_button.configure(state="disabled")
        self.status_label.configure(text="Status: Listening...")
        self.show_message("DEX is listening. Speak now...")

        thread = threading.Thread(
            target=self.listen_to_user,
            daemon=True
        )
        thread.start()

    # Record and recognize speech
    def listen_to_user(self):
        try:
            duration = 5
            sample_rate = 16000
            total_start = time.time()

            audio_data = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="int16"
            )

            sd.wait()
            recording_end = time.time()
            audio = sr.AudioData(
                audio_data.tobytes(),
                sample_rate,
                2
            )

            # FLAC conversion workaround for Apple Silicon
            def encode_flac(convert_rate=None, convert_width=None):
                samples = np.frombuffer(
                    audio.frame_data,
                    dtype="<i2"
                )

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

            # Convert speech into text
            text = recognizer.recognize_google(audio)
            recognition_end = time.time()

            self.after(
                0,
                lambda: self.show_message(
                    "You said: " + text + "\n\nDEX is thinking..."
                )
            )

            # Send recognized text to Gemini
            gemini_response = self.ask_gemini(text)
            gemini_end = time.time()

            print("\n--- DEX PERFORMANCE ---")
            print("Recording:", round(recording_end - total_start, 2), "seconds")
            print("Speech recognition:", round(recognition_end - recording_end, 2), "seconds")
            print("Gemini response:", round(gemini_end - recognition_end, 2), "seconds")
            print("Total:", round(gemini_end - total_start, 2), "seconds")
            print("-----------------------\n")

            # Display Gemini response
            self.after(
                0,
                lambda: self.finish_listening(
                    "You said: " + text +
                    "\n\nDEX:\n" + gemini_response
                )
            )

        except sr.UnknownValueError:
            self.after(
                0,
                lambda: self.finish_listening(
                    "Sorry, I couldn't understand your voice."
                )
            )

        except Exception as e:
            error_message = str(e)

            self.after(
                0,
                lambda: self.finish_listening(
                    "Error: " + error_message
                )
            )

    # Communicate with Gemini
    def ask_gemini(self, user_text):
        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-3.5-flash",
                contents=user_text
            )

            return response.text or "DEX couldn't generate a response."

        except Exception as e:
            return "Gemini Error: " + str(e)

    # Finish listening
    def finish_listening(self, message):
        self.show_message(message)
        self.status_label.configure(text="Status: Ready")
        self.mic_button.configure(state="normal")


if __name__ == "__main__":
    app = DEXAssistant()
    print("DEX WITH GEMINI IS RUNNING")
    app.mainloop()
