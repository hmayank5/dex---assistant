
import os
from dotenv import load_dotenv
from google import genai

# Load API key from .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Gemini API key not found in .env")

# Connect to Gemini
client = genai.Client(api_key=api_key)

# Send a test command
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="Explain what a voice assistant does in two simple sentences."
)

print("\nDEX - Gemini Response:\n")
print(response.text)
