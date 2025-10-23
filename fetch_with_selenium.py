#!/usr/bin/env python3
"""
Fetch HTML content using Selenium with headless Chrome to bypass bot protection.
"""

import argparse
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time


def fetch_page_selenium(url: str, output_file: str = None, wait_time: int = 5):
    """Fetch a page using headless Chrome."""

    print(f"Initializing headless Chrome browser...")

    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Set user agent
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = None
    try:
        # Try to install and use ChromeDriver
        print("Installing/locating ChromeDriver...")
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())

        print("Starting browser...")
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Hide webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print(f"Fetching: {url}")
        driver.get(url)

        # Wait for page to load
        print(f"Waiting {wait_time} seconds for page to fully load...")
        time.sleep(wait_time)

        # Get page source
        html = driver.page_source

        print(f"Successfully fetched {len(html)} bytes")

        # Save to file if specified
        if output_file:
            Path(output_file).write_text(html, encoding='utf-8')
            print(f"Saved to: {output_file}")
        else:
            print("\n" + "="*80)
            print("HTML CONTENT:")
            print("="*80)
            print(html[:2000])  # Print first 2000 chars
            if len(html) > 2000:
                print(f"\n... ({len(html) - 2000} more bytes) ...")

        return html

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None

    finally:
        if driver:
            print("Closing browser...")
            driver.quit()


def main():
    parser = argparse.ArgumentParser(
        description='Fetch HTML using Selenium with headless Chrome'
    )
    parser.add_argument(
        'url',
        help='URL to fetch'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (optional)'
    )
    parser.add_argument(
        '-w', '--wait',
        type=int,
        default=5,
        help='Wait time in seconds for page to load (default: 5)'
    )

    args = parser.parse_args()

    html = fetch_page_selenium(args.url, args.output, args.wait)

    if not html:
        sys.exit(1)


if __name__ == '__main__':
    main()
