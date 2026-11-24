
import customtkinter as ctk

# Configure appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DEXAssistant(ctk.CTk):

    def __init__(self):
        super().__init__()

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

        self.subtitle = ctk.CTkLabel(
            self,
            text="YOUR INTELLIGENT DESKTOP ASSISTANT",
            font=("Arial", 13)
        )
        self.subtitle.pack(pady=5)

        # Assistant status
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

        # Response area
        self.response_box = ctk.CTkTextbox(
            self,
            width=550,
            height=180,
            font=("Arial", 14)
        )
        self.response_box.pack(pady=20)

        self.response_box.insert(
            "0.0",
            "Hello! I am DEX.\n\nYour intelligent voice and gesture assistant.\n\nWaiting for your command..."
        )

        self.response_box.configure(state="disabled")

    def activate_assistant(self):
        self.status_label.configure(
            text="Status: Activated"
        )

        self.response_box.configure(state="normal")
        self.response_box.delete("0.0", "end")
        self.response_box.insert(
            "0.0",
            "DEX is ready!\n\nVoice recognition will be integrated in the next stage."
        )
        self.response_box.configure(state="disabled")


if __name__ == "__main__":
    app = DEXAssistant()
    app.mainloop()
