from src.browser_control import BrowserController

browser = BrowserController()

result = browser.search_amazon("wireless headphones")

print(result)

input("Press Enter to close the browser...")

browser.close_browser()