
from desktop_control import DesktopController
import time

desktop = DesktopController()

print(desktop.get_screen_size())

print("Taking screenshot in 3 seconds...")
time.sleep(3)

screenshot = desktop.take_screenshot()
screenshot.save("dex_test_screenshot.png")

print("Screenshot saved successfully.")
