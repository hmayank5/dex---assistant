
import pyautogui
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
import json
import time

from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from browser_control import BrowserController
from desktop_control import DesktopController


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

MODEL_NAME = "gemini-3.5-flash"

SAMPLE_RATE = 16000
MAX_COMMAND_SECONDS = 6
SILENCE_SECONDS = 0.65
START_TIMEOUT_SECONDS = 3
AUDIO_BLOCK_SECONDS = 0.10
VOICE_THRESHOLD = 180

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

        self.gemini_client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=30000)
        )

        self.browser_controller = BrowserController()
        self.desktop_controller = DesktopController()

        # Listening controls
        self.stop_event = threading.Event()
        self.is_listening = False
        self.listening_thread = None
        self.speech_process = None

        # Pending screen-aware click
        self.pending_click = None
        self.pending_click_timeout = 30

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

        self.status_label.configure(
            text="Status: " + message
        )

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

        if self.speech_process is not None:

            if self.speech_process.poll() is None:
                self.speech_process.terminate()

        self.update_status("Stopping...")
        self.show_message("DEX stopped by user.")

    def on_listening_stopped(self):

        self.is_listening = False
        self.listening_thread = None

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

        if self.speech_process is not None:

            if self.speech_process.poll() is None:
                self.speech_process.terminate()

        self.destroy()

    # --------------------------------------------------
    # TEXT TO SPEECH
    # --------------------------------------------------

    def speak_text(self, message):

        try:

            spoken_text = re.sub(
                r"https?://\S+",
                "",
                message
            )

            spoken_text = re.split(
                r"\n\s*Sources:",
                spoken_text,
                maxsplit=1
            )[0]

            spoken_text = spoken_text.strip()

            if not spoken_text or self.stop_event.is_set():
                return

            spoken_text = spoken_text[:1500]

            self.speech_process = subprocess.Popen(
                ["say", spoken_text]
            )

            recognizer = sr.Recognizer()

            # Monitor voice stop commands during speech
            while self.speech_process.poll() is None:

                if self.stop_event.is_set():
                    self.speech_process.terminate()
                    break

                try:

                    audio_data = sd.rec(
                        int(1.2 * SAMPLE_RATE),
                        samplerate=SAMPLE_RATE,
                        channels=1,
                        dtype="int16"
                    )

                    sd.wait()

                    if self.stop_event.is_set():
                        self.speech_process.terminate()
                        break

                    volume = np.sqrt(
                        np.mean(
                            audio_data.astype(np.float32) ** 2
                        )
                    )

                    if volume < 120:
                        continue

                    audio = sr.AudioData(
                        audio_data.tobytes(),
                        SAMPLE_RATE,
                        2
                    )

                    audio.get_flac_data = (
                        lambda convert_rate=None, convert_width=None:
                        self.convert_audio_to_flac(audio)
                    )

                    recognized_text = recognizer.recognize_google(
                        audio
                    ).lower().strip()

                    print(
                        "Speech monitor heard:",
                        recognized_text
                    )

                    stop_phrases = [
                        "dex stop",
                        "stop dex",
                        "hey dex stop",
                        "deactivate dex",
                        "stop listening"
                    ]

                    if any(
                        phrase in recognized_text
                        for phrase in stop_phrases
                    ):

                        print("Voice stop command detected.")

                        self.stop_event.set()
                        self.speech_process.terminate()
                        break

                except (sr.UnknownValueError, sr.RequestError):
                    continue

                except Exception as e:

                    print("Speech monitoring error:", e)
                    continue

        except Exception as e:

            print("Speech error:", e)

        finally:

            if self.speech_process is not None:

                if self.speech_process.poll() is None:
                    self.speech_process.terminate()

                self.speech_process = None

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
    # SCREENSHOT PREPARATION
    # --------------------------------------------------

    def prepare_screenshot(self):

        screenshot = self.desktop_controller.take_screenshot()

        original_width, original_height = screenshot.size

        screenshot.thumbnail((1280, 1280))

        image_buffer = io.BytesIO()

        screenshot.convert("RGB").save(
            image_buffer,
            format="JPEG",
            quality=65
        )

        image_bytes = image_buffer.getvalue()

        return image_bytes, original_width, original_height

    # --------------------------------------------------
    # SCREEN UNDERSTANDING
    # --------------------------------------------------

    def analyze_screen(self, user_question):

        try:

            self.after(
                0,
                lambda: self.update_status("Capturing screen...")
            )

            image_bytes, width, height = self.prepare_screenshot()

            print("DEX: Screenshot captured and compressed.")

            self.after(
                0,
                lambda: self.update_status("Sending to Gemini...")
            )

            prompt = (
                "You are DEX, a desktop assistant.\n"
                "Analyze this screenshot carefully.\n"
                "Describe visible content clearly.\n"
                "Read visible text when requested.\n"
                "Explain visible errors in simple language.\n"
                "Do not guess information that is not visible.\n\n"
                f"Original screenshot dimensions: {width} x {height}\n"
                f"User question: {user_question}"
            )

            response = self.gemini_client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg"
                    )
                ]
            )

            print("DEX: Gemini response received.")

            return response.text or "Gemini returned an empty response."

        except Exception as e:

            print("Screen analysis error:", repr(e))

            return "Screen analysis failed:\n" + str(e)

        finally:

            try:

                self.after(
                    0,
                    lambda: self.update_status(
                        "Listening..." if self.is_listening else "Ready"
                    )
                )

            except Exception:
                pass

    # --------------------------------------------------
    # SCREEN-AWARE ELEMENT LOCATION
    # --------------------------------------------------

    def extract_element_target(self, command):

        patterns = [
            r"^(?:find|locate)\s+(?:the\s+)?(.+)$",
            r"^point\s+to\s+(?:the\s+)?(.+)$",
            r"^move\s+cursor\s+to\s+(?:the\s+)?(.+)$",
            r"^show\s+me\s+where\s+(?:the\s+)?(.+?)\s+is$",
            r"^where\s+is\s+(?:the\s+)?(.+)$"
        ]

        ui_element_words = [
            "button",
            "icon",
            "field",
            "textbox",
            "text box",
            "input",
            "textarea",
            "text area",
            "email field",
            "name field",
            "password field",
            "search input",
            "search field",
            "username field",
            "phone field",
            "link",
            "menu",
            "tab",
            "checkbox",
            "check box",
            "dropdown",
            "drop-down",
            "search bar",
            "window",
            "close button",
            "submit",
            "login",
            "sign in"
        ]

        for pattern in patterns:

            match = re.match(pattern, command, re.IGNORECASE)

            if match:

                target = match.group(1).strip(" .,!?:;")

                if any(
                    word in target.lower()
                    for word in ui_element_words
                ):

                    return target

        return None

    def locate_screen_element(self, target):

        try:

            self.pending_click = None

            self.after(
                0,
                lambda: self.update_status(
                    "Locating " + target + "..."
                )
            )

            self.after(
                0,
                lambda: self.show_message(
                    "DEX is examining your screen to locate:\n\n"
                    + target
                )
            )

            image_bytes, width, height = self.prepare_screenshot()

            prompt = f"""
You are the visual element locator for DEX, a desktop assistant.

Find this exact visible user-interface element:

TARGET: {target}

Original screenshot dimensions:
Width: {width}
Height: {height}

Return ONLY valid JSON. Do not use Markdown.

If the element is visible, return:

{{
  "found": true,
  "element": "short description",
  "x_min": 100,
  "y_min": 100,
  "x_max": 300,
  "y_max": 200
}}

Coordinates must be normalized from 0 to 1000.

For example:
- x_min 0 means the extreme left.
- x_max 1000 means the extreme right.
- y_min 0 means the top.
- y_max 1000 means the bottom.

The coordinates must describe the bounding box of the requested element.

If the element cannot be identified confidently, return:

{{
  "found": false,
  "element": "{target}",
  "reason": "Brief explanation"
}}

Do not guess coordinates.
Do not select a similar-looking element when the requested one is unclear.
"""

            response = self.gemini_client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg"
                    )
                ]
            )

            response_text = response.text or ""

            print("DEX locator response:", response_text)

            # Extract JSON
            json_match = re.search(
                r"\{.*\}",
                response_text,
                re.DOTALL
            )

            if not json_match:

                return (
                    "DEX couldn't understand Gemini's location result. "
                    "Please try again."
                )

            result = json.loads(json_match.group(0))

            if not result.get("found", False):

                reason = result.get(
                    "reason",
                    "The element was not clearly visible."
                )

                return (
                    "DEX couldn't confidently locate "
                    + target + ".\n"
                    + str(reason)
                )

            # Read and validate coordinates
            x_min = float(result["x_min"])
            y_min = float(result["y_min"])
            x_max = float(result["x_max"])
            y_max = float(result["y_max"])

            coordinates = [
                x_min,
                y_min,
                x_max,
                y_max
            ]

            if not all(
                0 <= value <= 1000
                for value in coordinates
            ):

                return "DEX received coordinates outside the valid range."

            if x_min >= x_max or y_min >= y_max:

                return "DEX received an invalid element boundary."

            # Calculate centre of the bounding box
            center_x = (x_min + x_max) / 2
            center_y = (y_min + y_max) / 2

            screen_width, screen_height = pyautogui.size()

            screen_x = int(
                round((center_x / 1000) * (screen_width - 1))
            )

            screen_y = int(
                round((center_y / 1000) * (screen_height - 1))
            )

            # Final screen-boundary validation
            if not (
                0 <= screen_x < screen_width
                and 0 <= screen_y < screen_height
            ):

                return "DEX calculated an invalid screen position."

            # Store pending click
            self.pending_click = {
                "element": str(
                    result.get("element", target)
                ),
                "x": screen_x,
                "y": screen_y,
                "created_at": time.monotonic()
            }

            # Move cursor without clicking
            self.desktop_controller.move_mouse(
                screen_x,
                screen_y
            )

            return (
                "DEX located: "
                + self.pending_click["element"]
                + "\n\n"
                + f"Estimated position: {screen_x}, {screen_y}"
                + "\n\n"
                + "I have moved the cursor there without clicking."
                + "\n\n"
                + "Check the cursor position."
                + "\n"
                + "Say CONFIRM CLICK to click."
                + "\n"
                + "Say CANCEL CLICK to cancel."
                + "\n\n"
                + "This location is an estimate, not a guarantee."
            )

        except json.JSONDecodeError:

            return (
                "DEX received an invalid location response. "
                "Please try again."
            )

        except Exception as e:

            print("Element location error:", repr(e))

            return "Element location failed:\n" + str(e)

        finally:

            try:

                self.after(
                    0,
                    lambda: self.update_status(
                        "Listening..." if self.is_listening else "Ready"
                    )
                )

            except Exception:
                pass

    # --------------------------------------------------
    # CONFIRM OR CANCEL A PENDING CLICK
    # --------------------------------------------------

    def confirm_pending_click(self):

        if self.pending_click is None:

            return (
                "There is no pending screen-aware click. "
                "Ask me to locate an element first."
            )

        pending = self.pending_click

        # Check expiry
        elapsed = time.monotonic() - pending["created_at"]

        if elapsed > self.pending_click_timeout:

            self.pending_click = None

            return (
                "The pending click has expired. "
                "Please locate the element again."
            )

        x = pending["x"]
        y = pending["y"]

        screen_width, screen_height = pyautogui.size()

        if not (
            0 <= x < screen_width
            and 0 <= y < screen_height
        ):

            self.pending_click = None

            return "The saved screen position is no longer valid."

        # Clear pending state before clicking
        self.pending_click = None

        # Perform the confirmed click
        pyautogui.click(x, y)

        return (
            "Confirmed. DEX clicked the estimated position of "
            + pending["element"]
            + "."
        )

    def cancel_pending_click(self):

        if self.pending_click is None:

            return "There is no pending click to cancel."

        element = self.pending_click["element"]

        self.pending_click = None

        return (
            "Cancelled. DEX will not click "
            + element
            + "."
        )

    # --------------------------------------------------
    # RESPONSIVE VOICE CAPTURE (VOICE ACTIVITY DETECTION)
    # --------------------------------------------------

    def record_command_audio(self):
        """Record until a short pause after speech, instead of waiting 5 seconds."""
        chunks = []
        speech_started = False
        silence_time = 0.0
        elapsed = 0.0
        block_frames = int(SAMPLE_RATE * AUDIO_BLOCK_SECONDS)

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=block_frames
            ) as stream:
                while not self.stop_event.is_set():
                    chunk, overflowed = stream.read(block_frames)
                    chunk = np.asarray(chunk, dtype=np.int16).reshape(-1)
                    level = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
                    chunks.append(chunk.copy())
                    elapsed += AUDIO_BLOCK_SECONDS

                    if level >= VOICE_THRESHOLD:
                        speech_started = True
                        silence_time = 0.0
                    elif speech_started:
                        silence_time += AUDIO_BLOCK_SECONDS

                    if speech_started and silence_time >= SILENCE_SECONDS:
                        break
                    if not speech_started and elapsed >= START_TIMEOUT_SECONDS:
                        return None
                    if elapsed >= MAX_COMMAND_SECONDS:
                        break

            if self.stop_event.is_set() or not speech_started:
                return None

            audio_data = np.concatenate(chunks)
            return sr.AudioData(audio_data.tobytes(), SAMPLE_RATE, 2)

        except Exception as e:
            print("Microphone capture error:", repr(e))
            return None

    # --------------------------------------------------
    # CONTINUOUS VOICE RECOGNITION
    # --------------------------------------------------

    def listen_continuously(self):

        recognizer = sr.Recognizer()

        while not self.stop_event.is_set():

            try:

                audio = self.record_command_audio()

                if audio is None or self.stop_event.is_set():
                    continue

                audio.get_flac_data = (
                    lambda convert_rate=None, convert_width=None:
                    self.convert_audio_to_flac(audio)
                )

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

                command = recognized_text.lower().strip()

                # Stop command
                if any(
                    phrase in command
                    for phrase in [
                        "stop dex",
                        "dex stop",
                        "hey dex stop",
                        "deactivate dex",
                        "stop listening"
                    ]
                ):

                    self.stop_event.set()

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

        try:

            self.after(
                0,
                self.on_listening_stopped
            )

        except Exception:
            pass

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
    # DESKTOP CONTROL COMMANDS
    # --------------------------------------------------

    def handle_desktop_command(self, command):

        command = command.lower().strip()

        # CLICK
        if command in ["click", "click here"]:

            if self.pending_click is not None:

                return (
                    "A screen-aware click is pending. "
                    "Please say CONFIRM CLICK or CANCEL CLICK."
                )

            return self.desktop_controller.click()

        # TYPE TEXT
        type_match = re.match(
            r"^(?:type|write)\s+(.+)$",
            command
        )

        if type_match:

            text_to_type = type_match.group(1).strip()

            if len(text_to_type) > 500:

                return "Please keep the text under 500 characters."

            return self.desktop_controller.type_text(
                text_to_type
            )

        # SCROLL
        if command in ["scroll down", "scroll up"]:

            direction = command.split()[-1]

            return self.desktop_controller.scroll(
                direction,
                3
            )

        # KEYBOARD
        key_commands = {

            "press enter": "enter",
            "press tab": "tab",
            "press escape": "esc",
            "press space": "space",
            "press backspace": "backspace",
            "press delete": "delete",
            "press up": "up",
            "press down": "down",
            "press left": "left",
            "press right": "right"
        }

        if command in key_commands:

            key = key_commands[command]

            return self.desktop_controller.press_key(key)

        # MOVE MOUSE TO SCREEN CENTRE
        if command in [
            "move mouse to center",
            "move mouse to centre"
        ]:

            width, height = pyautogui.size()

            return self.desktop_controller.move_mouse(
                width // 2,
                height // 2
            )

        return None

    # --------------------------------------------------
    # MAIN COMMAND HANDLER
    # --------------------------------------------------

    def handle_command(self, user_text):

        command = user_text.lower().strip()
        print("DEX DEBUG: Received command:", command)

        # Confirm/cancel are local actions: check them before any Gemini call.
        if command in [
            "cancel click", "cancel the click", "cancel that click",
            "don't click", "do not click", "cancel"
        ]:
            return self.cancel_pending_click()

        if command in [
            "confirm click", "yes confirm click", "confirm the click",
            "click the located element"
        ]:
            return self.confirm_pending_click()

        # Locate an element on the currently visible screen.
        target = self.extract_element_target(command)
        print("DEX DEBUG: Detected element:", target)

        if target:
            print("DEX DEBUG: Starting screen element location")
            return self.locate_screen_element(target)

        # EXISTING DESKTOP CONTROL
        desktop_response = self.handle_desktop_command(command)

        if desktop_response is not None:
            return desktop_response

        # SCREEN UNDERSTANDING
        screen_commands = [

            "what is on my screen",
            "what do you see on my screen",
            "describe my screen",
            "analyze my screen",
            "analyse my screen",
            "read my screen",
            "what is this error",
            "explain this error",
            "what is displayed on my screen"
        ]

        if any(
            phrase in command
            for phrase in screen_commands
        ):

            return self.analyze_screen(user_text)

        # AMAZON SEARCH
        if "amazon" in command and any(
            word in command
            for word in [
                "search",
                "find",
                "look for",
                "show me"
            ]
        ):

            product = self.extract_query(
                command,
                "amazon"
            )

            if product:

                return self.browser_controller.search_amazon(
                    product
                )

            return self.browser_controller.open_website(
                "https://www.amazon.in",
                "Amazon"
            )

        # GOOGLE SEARCH WITH WEB SUMMARY
        if "google" in command and any(
            word in command
            for word in [
                "search",
                "find",
                "look for",
                "show me"
            ]
        ):

            query = self.extract_query(
                command,
                "google"
            )

            if query:

                self.browser_controller.search_google(query)

                return self.search_google_and_summarize(
                    query
                )

        # YOUTUBE SEARCH
        if "youtube" in command and any(
            word in command
            for word in [
                "search",
                "find",
                "look for",
                "show me"
            ]
        ):

            query = self.extract_query(
                command,
                "youtube"
            )

            if query:

                return self.browser_controller.search_youtube(
                    query
                )

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

        if any(
            word in command
            for word in [
                "open",
                "launch",
                "start",
                "go to"
            ]
        ):

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

                            sources.append(
                                (title, url)
                            )

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

    print("DEX SCREEN-AWARE CONTROL IS RUNNING")

    app.mainloop()
