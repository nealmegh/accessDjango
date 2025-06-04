from playwright.sync_api import sync_playwright
import os
import uuid

def capture_screenshot(url):
    try:
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join("core", "static", "screenshots", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            page.screenshot(path=filepath, full_page=True)
            browser.close()

        return f"screenshots/{filename}"
    except Exception as e:
        print("Screenshot error:", e)
        return None
