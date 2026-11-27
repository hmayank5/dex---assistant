
import pyautogui
import time


class DesktopController:

    def move_mouse(self, x, y):
        pyautogui.moveTo(x, y, duration=0.3)
        return f"Mouse moved to {x}, {y}."

    def click(self):
        pyautogui.click()
        return "Clicked."

    def type_text(self, text):
        pyautogui.write(text, interval=0.03)
        return "Text typed."

    def press_key(self, key):
        pyautogui.press(key)
        return f"Pressed {key}."

    def scroll(self, direction, amount=3):
        if direction == "down":
            pyautogui.scroll(-amount)
        elif direction == "up":
            pyautogui.scroll(amount)
        return f"Scrolled {direction}."

    def get_screen_size(self):
        width, height = pyautogui.size()
        return f"Screen size: {width} x {height}."

    def take_screenshot(self):
        screenshot = pyautogui.screenshot()
        return screenshot
