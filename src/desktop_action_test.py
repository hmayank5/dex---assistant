
import pyautogui
import time

print("DEX desktop control test starting...")

# Display screen dimensions
print("Screen size:", pyautogui.size())

# Move mouse to the centre of the screen
width, height = pyautogui.size()

pyautogui.moveTo(
    width // 2,
    height // 2,
    duration=1
)

print("Mouse movement successful!")

print("Click test begins in 5 seconds.")
print("Place your mouse over a blank TextEdit document.")

time.sleep(5)

# Click at the current mouse position
pyautogui.click()

# Type harmless test text
pyautogui.write(
    "DEX desktop control is working!",
    interval=0.05
)

print("Mouse click and keyboard test successful!")
