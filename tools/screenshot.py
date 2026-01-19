#!/usr/bin/env python3
"""Screenshot tool for debugging GUI issues.

Usage:
    python tools/screenshot.py [url] [output]

Examples:
    python tools/screenshot.py http://localhost:5173
    python tools/screenshot.py http://localhost:5173/story /tmp/story.png
    python tools/screenshot.py http://localhost:5173/voice /tmp/voice.png
"""

import sys
import subprocess
from pathlib import Path


def take_screenshot(url: str = "http://localhost:5173", output: str = "/tmp/gui_screenshot.png") -> str:
    """Take a screenshot of a URL using Chrome headless."""
    # Try different Chrome executable names
    chrome_paths = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/snap/bin/chromium",
    ]

    chrome = None
    for path in chrome_paths:
        try:
            result = subprocess.run([path, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                chrome = path
                break
        except FileNotFoundError:
            continue

    if not chrome:
        return "ERROR: Chrome/Chromium not found. Please install Chrome or Chromium."

    # Take screenshot
    args = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--screenshot={output}",
        "--window-size=1280,900",
        "--hide-scrollbars",
        url,
    ]

    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if Path(output).exists():
            return f"Screenshot saved to: {output}"
        else:
            return f"ERROR: Screenshot failed. stderr: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "ERROR: Screenshot timed out after 30 seconds"
    except Exception as e:
        return f"ERROR: {str(e)}"


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
    output = sys.argv[2] if len(sys.argv) > 2 else "/tmp/gui_screenshot.png"

    print(f"Taking screenshot of {url}...")
    result = take_screenshot(url, output)
    print(result)


if __name__ == "__main__":
    main()
