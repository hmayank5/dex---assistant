
import customtkinter as ctk
import speech_recognition as sr
import sounddevice as sd
import numpy as np
import soundfile as sf
import io
import threading

# Configure appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DEXAssistant(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("DEX - Desktop Assistant")
        self.geometry("800x600")
        self.minsize(650, 500)

        self.title_label = ctk.CTkLabel(
            self,
            text="DEX",
            font=("Arial", 42, "bold")
        )
        self.title_label.pack(pady=(35, 5))

        self.subtitle = ctk.CTkLabel(
            self,
            text="YOUR INTELLIGENT DESKTOP ASSISTANT",
            font=("Arial", 13)
        )
        self.subtitle.pack(pady=5)

        self.status_label = ctk.CTkLabel(
            self,
            text="Status: Ready",
            font=("Arial", 14)
        )
        self.status_label.pack(pady=20)

        self.mic_button = ctk.CTkButton(
            self,
            text="ACTIVATE DEX",
            width=200,
            height=55,
            font=("Arial", 16, "bold"),
            command=self.activate_assistant
        )
        self.mic_button.pack(pady=15)

        self.gesture_label = ctk.CTkLabel(
            self,
            text="Gesture Sensor: Not Connected",
            font=("Arial", 13)
        )
        self.gesture_label.pack(pady=10)

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

    def show_message(self, message):
        self.response_box.configure(state="normal")
        self.response_box.delete("0.0", "end")
        self.response_box.insert("0.0", message)
        self.response_box.configure(state="disabled")

    def activate_assistant(self):
        self.mic_button.configure(state="disabled")
        self.status_label.configure(text="Status: Listening...")
        self.show_message("DEX is listening. Speak now...")

        # Run microphone recording in a separate thread
        thread = threading.Thread(
            target=self.listen_to_user,
            daemon=True
        )
        thread.start()

    def listen_to_user(self):
        try:
            duration = 5
            sample_rate = 16000

            audio_data = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="int16"
            )

            sd.wait()

            audio = sr.AudioData(
                audio_data.tobytes(),
                sample_rate,
                2
            )

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

            text = recognizer.recognize_google(audio)

            self.after(
                0,
                lambda: self.finish_listening(
                    "You said: " + text
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

    def finish_listening(self, message):
        self.show_message(message)
        self.status_label.configure(text="Status: Ready")
        self.mic_button.configure(state="normal")


if __name__ == "__main__":
    app = DEXAssistant()
    print("NEW DEX CODE IS RUNNING")
    app.mainloop()
