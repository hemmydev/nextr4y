#!/usr/bin/env python3
"""
Fetch HTML content using requests-html with JavaScript rendering.
"""

import argparse
import sys
from pathlib import Path
from requests_html import HTMLSession


def fetch_page_with_js(url: str, output_file: str = None, render_timeout: int = 20):
    """Fetch a page and render JavaScript."""

    print(f"Fetching: {url}")

    session = HTMLSession()

    try:
        # Fetch the page
        response = session.get(url, timeout=30)
        response.raise_for_status()

        print(f"Initial fetch successful (status: {response.status_code})")
        print(f"Content length before JS rendering: {len(response.html.html)} bytes")

        # Render JavaScript
        print(f"Rendering JavaScript (timeout: {render_timeout}s)...")
        response.html.render(timeout=render_timeout, sleep=2)

        html = response.html.html
        print(f"Content length after JS rendering: {len(html)} bytes")
        print(f"Successfully fetched and rendered page")

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
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description='Fetch HTML using requests-html with JavaScript rendering'
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
        '-t', '--timeout',
        type=int,
        default=20,
        help='Render timeout in seconds (default: 20)'
    )

    args = parser.parse_args()

    html = fetch_page_with_js(args.url, args.output, args.timeout)

    if not html:
        sys.exit(1)


if __name__ == '__main__':
    main()
