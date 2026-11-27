
import subprocess
from urllib.parse import quote_plus


class BrowserController:

    def open_chrome(self):
        try:
            subprocess.Popen(["open", "-a", "Google Chrome"])
            return "Opening Google Chrome."

        except Exception as e:
            return "Could not open Chrome: " + str(e)

    def open_website(self, url, name):
        try:
            subprocess.Popen([
                "open",
                "-a",
                "Google Chrome",
                url
            ])
            return f"Opening {name} in Google Chrome."

        except Exception as e:
            return "Browser Error: " + str(e)

    def search_amazon(self, product):
        if not product.strip():
            return "Please specify a product."

        url = (
            "https://www.amazon.in/s?k="
            + quote_plus(product)
        )

        return self.open_website(url, "Amazon search")

    def search_google(self, query):
        if not query.strip():
            return "Please specify what to search for."

        url = (
            "https://www.google.com/search?q="
            + quote_plus(query)
        )

        return self.open_website(url, "Google search")

    def search_youtube(self, query):
        if not query.strip():
            return "Please specify what to search for."

        url = (
            "https://www.youtube.com/results?search_query="
            + quote_plus(query)
        )

        return self.open_website(url, "YouTube search")

    def close_browser(self):
        return "No separate browser session is running."
