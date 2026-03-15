#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["trafilatura"]
# ///
"""Fetch URL and extract clean article text via trafilatura."""

import ipaddress
import json
import signal
import sys
from urllib.parse import urlparse

from trafilatura import bare_extraction, fetch_url
from trafilatura.settings import use_config

# Hard timeout: 15s total (fetch + extract). Prevents hung network stalls.
signal.signal(signal.SIGALRM, lambda *_: sys.exit(124))
signal.alarm(15)


def _error(url, status):
    json.dump({"url": url, "status": status, "text": "", "title": "", "date": "", "total_chars": 0, "truncated": False}, sys.stdout)
    sys.exit(0)


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_clean.py --url-file <path> [max_chars]", file=sys.stderr)
        sys.exit(1)

    # Read URL from file (--url-file <path>) to avoid shell injection
    if sys.argv[1] == "--url-file":
        if len(sys.argv) < 3:
            print("Missing path after --url-file", file=sys.stderr)
            sys.exit(1)
        try:
            url = open(sys.argv[2]).read().strip()
        except OSError:
            _error("", "fetch_failed")
            return
        max_chars_arg = sys.argv[3] if len(sys.argv) > 3 else "3000"
    else:
        url = sys.argv[1]
        max_chars_arg = sys.argv[2] if len(sys.argv) > 2 else "3000"

    if not url:
        _error("", "fetch_failed")
        return

    # SSRF guard: reject non-HTTP schemes and private/loopback destinations
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            _error(url, "fetch_failed")
            return
        hostname = parsed.hostname or ""
        if hostname in ("localhost", "") or hostname.endswith(".local"):
            _error(url, "fetch_failed")
            return
        try:
            addr = ipaddress.ip_address(hostname)
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                _error(url, "fetch_failed")
                return
        except ValueError:
            pass  # hostname is a domain, not an IP — OK
    except Exception:
        _error(url, "fetch_failed")
        return

    try:
        max_chars = int(max_chars_arg)
    except ValueError:
        max_chars = 3000

    config = use_config()
    config.set("DEFAULT", "DOWNLOAD_TIMEOUT", "10")

    html = fetch_url(url, config=config)
    if not html:
        _error(url, "fetch_failed")
        return

    doc = bare_extraction(
        html,
        url=url,
        favor_precision=True,
        include_comments=False,
        include_links=False,
        include_tables=True,
        deduplicate=True,
        fast=True,
    )

    if not doc or not doc.text or len(doc.text) < 100:
        _error(url, "extraction_failed")
        return

    text = doc.text
    total_chars = len(text)
    if total_chars > max_chars:
        text = text[:max_chars]
        truncated = True
    else:
        truncated = False

    json.dump({
        "url": url,
        "status": "ok",
        "title": doc.title or "",
        "date": doc.date or "",
        "text": text,
        "total_chars": total_chars,
        "truncated": truncated,
    }, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
