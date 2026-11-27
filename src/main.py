
import customtkinter as ctk
import speech_recognition as sr
import sounddevice as sd
import numpy as np
import soundfile as sf
import io
import threading
import subprocess
import os
import re

from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from browser_control import BrowserController


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

MODEL_NAME = "gemini-3.5-flash"

SAMPLE_RATE = 16000
RECORDING_DURATION = 5

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# --------------------------------------------------
# DEX ASSISTANT
# --------------------------------------------------

class DEXAssistant(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Gemini API setup
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("Gemini API key not found in .env")

        self.gemini_client = genai.Client(api_key=api_key)
        self.browser_controller = BrowserController()

        # Listening controls
        self.stop_event = threading.Event()
        self.is_listening = False
        self.listening_thread = None

        # Window configuration
        self.title("DEX - Desktop Assistant")
        self.geometry("800x600")
        self.minsize(650, 500)

        # Main heading
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

        # Microphone button
        self.mic_button = ctk.CTkButton(
            self,
            text="ACTIVATE DEX",
            width=200,
            height=55,
            font=("Arial", 16, "bold"),
            command=self.toggle_assistant
        )
        self.mic_button.pack(pady=15)

        # Gesture sensor status
        self.gesture_label = ctk.CTkLabel(
            self,
            text="Gesture Sensor: Not Connected",
            font=("Arial", 13)
        )
        self.gesture_label.pack(pady=10)

        # Response display
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
            "Press ACTIVATE DEX to begin."
        )

        self.protocol("WM_DELETE_WINDOW", self.close_application)

    # --------------------------------------------------
    # GUI FUNCTIONS
    # --------------------------------------------------

    def show_message(self, message):
        self.response_box.configure(state="normal")
        self.response_box.delete("0.0", "end")
        self.response_box.insert("0.0", message)
        self.response_box.configure(state="disabled")

    def update_status(self, message):
        self.status_label.configure(text="Status: " + message)

    def toggle_assistant(self):

        if self.is_listening:
            self.stop_assistant()
        else:
            self.activate_assistant()

    def activate_assistant(self):

        if self.is_listening:
            return

        self.stop_event.clear()
        self.is_listening = True

        self.mic_button.configure(
            text="STOP DEX",
            state="normal"
        )

        self.update_status("Listening...")
        self.show_message("DEX is listening. Speak your commands.")

        self.listening_thread = threading.Thread(
            target=self.listen_continuously,
            daemon=True
        )

        self.listening_thread.start()

    def stop_assistant(self):

        if not self.is_listening:
            return

        self.stop_event.set()
        self.update_status("Stopping...")
        self.show_message("Stopping DEX listening...")

    def on_listening_stopped(self):

        self.is_listening = False

        self.mic_button.configure(
            text="ACTIVATE DEX",
            state="normal"
        )

        self.update_status("Ready")
        self.show_message(
            "DEX has stopped listening.\n\n"
            "Press ACTIVATE DEX to start again."
        )

    def close_application(self):

        self.stop_event.set()
        self.is_listening = False

        self.destroy()

    # --------------------------------------------------
    # TEXT TO SPEECH
    # --------------------------------------------------

    def speak_text(self, message):

        try:

            # Remove URLs before speaking
            spoken_text = re.sub(
                r"https?://\S+",
                "",
                message
            )

            # Don't read source links aloud
            spoken_text = re.split(
                r"\nSources:",
                spoken_text,
                maxsplit=1
            )[0]

            spoken_text = spoken_text.strip()

            if not spoken_text:
                return

            # Keep spoken responses reasonably short
            spoken_text = spoken_text[:1500]

            # macOS built-in voice
            subprocess.run(
                ["say", spoken_text],
                check=False
            )

        except Exception as e:
            print("Speech error:", e)

    # --------------------------------------------------
    # AUDIO CONVERSION
    # --------------------------------------------------

    def convert_audio_to_flac(self, audio):

        samples = np.frombuffer(
            audio.frame_data,
            dtype="<i2"
        )

        buffer = io.BytesIO()

        sf.write(
            buffer,
            samples,
            samplerate=SAMPLE_RATE,
            format="FLAC",
            subtype="PCM_16"
        )

        return buffer.getvalue()

    # --------------------------------------------------
    # CONTINUOUS VOICE RECOGNITION
    # --------------------------------------------------

    def listen_continuously(self):

        recognizer = sr.Recognizer()

        while not self.stop_event.is_set():

            try:

                # Record a five-second audio window
                audio_data = sd.rec(
                    int(RECORDING_DURATION * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="int16"
                )

                sd.wait()

                if self.stop_event.is_set():
                    break

                # Ignore silence and very quiet audio
                volume = np.sqrt(
                    np.mean(audio_data.astype(np.float32) ** 2)
                )

                if volume < 120:
                    continue

                audio = sr.AudioData(
                    audio_data.tobytes(),
                    SAMPLE_RATE,
                    2
                )

                # Use SoundFile for FLAC conversion
                audio.get_flac_data = (
                    lambda convert_rate=None, convert_width=None:
                    self.convert_audio_to_flac(audio)
                )

                # Convert speech to text
                try:

                    recognized_text = recognizer.recognize_google(
                        audio
                    )

                except sr.UnknownValueError:
                    continue

                if self.stop_event.is_set():
                    break

                print("You said:", recognized_text)

                self.after(
                    0,
                    lambda text=recognized_text:
                    self.show_message(
                        "You said: " + text +
                        "\n\nDEX is processing..."
                    )
                )

                # Stop command
                command = recognized_text.lower().strip()

                if any(phrase in command for phrase in [
                    "stop dex",
                    "deactivate dex",
                    "stop listening"
                ]):

                    self.after(
                        0,
                        lambda: self.show_message(
                            "Stop command received.\n\n"
                            "DEX is stopping listening now."
                        )
                    )

                    break

                # Process command
                response = self.handle_command(recognized_text)

                if self.stop_event.is_set():
                    break

                # Display response
                self.after(
                    0,
                    lambda text=recognized_text, reply=response:
                    self.show_message(
                        "You said: " + text +
                        "\n\nDEX:\n" + reply
                    )
                )

                # Speak response
                self.speak_text(response)

                # Continue listening after speaking

            except Exception as e:

                error_message = str(e)
                print("Listening error:", error_message)

                self.after(
                    0,
                    lambda error=error_message:
                    self.show_message(
                        "DEX encountered an error:\n" + error
                    )
                )

                break

        # Update GUI after listening stops
        self.after(0, self.on_listening_stopped)

    # --------------------------------------------------
    # SEARCH QUERY EXTRACTION
    # --------------------------------------------------

    def extract_query(self, command, website):

        patterns = [

            rf"\b(?:search|find|look for|show me)\s+"
            rf"(?:for\s+)?(.+?)\s+on\s+{website}\b",

            rf"\b{website}\b.*?\b"
            rf"(?:search|find|look for)\s+"
            rf"(?:for\s+)?(.+)$",

            rf"\b(?:search|find|look for)\s+"
            rf"(?:on\s+)?{website}\s+for\s+(.+)$"
        ]

        for pattern in patterns:

            match = re.search(pattern, command)

            if match:

                query = match.group(1).strip(" .,!?:;")

                query = re.sub(
                    r"^(a|an|the)\s+",
                    "",
                    query
                )

                query = re.sub(
                    r"\b(please|for me)$",
                    "",
                    query
                ).strip()

                if query:
                    return query

        return ""

    # --------------------------------------------------
    # MAIN COMMAND HANDLER
    # --------------------------------------------------

    def handle_command(self, user_text):

        command = user_text.lower().strip()

        # AMAZON SEARCH
        if "amazon" in command and any(
            word in command
            for word in ["search", "find", "look for", "show me"]
        ):

            product = self.extract_query(command, "amazon")

            if product:
                return self.browser_controller.search_amazon(product)

            return self.browser_controller.open_website(
                "https://www.amazon.in",
                "Amazon"
            )

        # GOOGLE SEARCH WITH WEB SUMMARY
        if "google" in command and any(
            word in command
            for word in ["search", "find", "look for", "show me"]
        ):

            query = self.extract_query(command, "google")

            if query:

                self.browser_controller.search_google(query)

                return self.search_google_and_summarize(query)

        # YOUTUBE SEARCH
        if "youtube" in command and any(
            word in command
            for word in ["search", "find", "look for", "show me"]
        ):

            query = self.extract_query(command, "youtube")

            if query:
                return self.browser_controller.search_youtube(query)

        # WEBSITE SHORTCUTS
        websites = {

            "google maps": (
                "https://maps.google.com",
                "Google Maps"
            ),

            "gmail": (
                "https://mail.google.com",
                "Gmail"
            ),

            "youtube": (
                "https://www.youtube.com",
                "YouTube"
            ),

            "maps": (
                "https://maps.google.com",
                "Google Maps"
            ),

            "google": (
                "https://www.google.com",
                "Google"
            ),

            "amazon": (
                "https://www.amazon.in",
                "Amazon"
            )
        }

        if any(word in command for word in [
            "open", "launch", "start", "go to"
        ]):

            for website, details in websites.items():

                if website in command:

                    return self.browser_controller.open_website(
                        details[0],
                        details[1]
                    )

            if "chrome" in command or "browser" in command:
                return self.browser_controller.open_chrome()

        # GENERAL QUESTIONS GO TO GEMINI
        return self.ask_gemini(user_text)

    # --------------------------------------------------
    # GOOGLE SEARCH + GEMINI SUMMARY
    # --------------------------------------------------

    def search_google_and_summarize(self, query):

        try:

            response = self.gemini_client.models.generate_content(

                model=MODEL_NAME,

                contents=(
                    f"Search the web for: {query}\n\n"
                    "Summarise the most useful and relevant findings. "
                    "Use clear, beginner-friendly language. "
                    "Keep the summary concise and mention important facts. "
                    "Do not invent facts or sources."
                ),

                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            google_search=types.GoogleSearch()
                        )
                    ]
                )
            )

            answer = response.text or "No summary was generated."

            # Retrieve source links
            sources = []

            if response.candidates:

                metadata = getattr(
                    response.candidates[0],
                    "grounding_metadata",
                    None
                )

                chunks = getattr(
                    metadata,
                    "grounding_chunks",
                    []
                ) if metadata else []

                for chunk in chunks:

                    web_source = getattr(
                        chunk,
                        "web",
                        None
                    )

                    if web_source:

                        title = getattr(
                            web_source,
                            "title",
                            "Web source"
                        )

                        url = getattr(
                            web_source,
                            "uri",
                            ""
                        )

                        if url and url not in [
                            source[1] for source in sources
                        ]:

                            sources.append((title, url))

            if sources:

                answer += "\n\nSources:\n"

                for title, url in sources[:5]:

                    answer += (
                        f"\n{title}\n"
                        f"{url}\n"
                    )

            return answer

        except Exception as e:

            error = str(e)

            if "503" in error or "UNAVAILABLE" in error:
                return (
                    "Google Search through Gemini is temporarily busy. "
                    "Please try again."
                )

            if "429" in error or "RESOURCE_EXHAUSTED" in error:
                return (
                    "Gemini request limit reached. "
                    "Please try again later."
                )

            return "Search Error: " + error

    # --------------------------------------------------
    # GENERAL GEMINI AI RESPONSE
    # --------------------------------------------------

    def ask_gemini(self, user_text):

        try:

            response = self.gemini_client.models.generate_content(
                model=MODEL_NAME,
                contents=user_text
            )

            return response.text or "DEX couldn't generate a response."

        except Exception as e:

            error = str(e)

            if "503" in error or "UNAVAILABLE" in error:
                return "Gemini is temporarily busy. Please try again."

            if "429" in error or "RESOURCE_EXHAUSTED" in error:
                return "Gemini request limit reached. Please try later."

            return "Gemini Error: " + error


# --------------------------------------------------
# RUN DEX
# --------------------------------------------------

if __name__ == "__main__":

    app = DEXAssistant()

    print("DEX CONTINUOUS LISTENING + VOICE OUTPUT IS RUNNING")

    app.mainloop()
