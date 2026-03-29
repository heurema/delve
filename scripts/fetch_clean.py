#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["trafilatura"]
# ///
"""Fetch URL and extract clean article text via trafilatura.

Optional quarry integration: if QUARRY_BIN env var is set (or quarry is in PATH),
extracted text is scanned for prompt injection patterns before output.
Quarry findings are included in the JSON response as 'quarry_findings'.
"""

import ipaddress
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import urllib.request
from urllib.parse import urlparse

from trafilatura import bare_extraction, fetch_url
from trafilatura.settings import use_config


def _is_blocked(addr):
    return not addr.is_global or addr.is_loopback


class _SSRFSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block redirects to private/internal IP addresses."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        hostname = parsed.hostname or ""
        if hostname in ("localhost", "") or hostname.endswith(".local"):
            raise urllib.error.URLError("redirect to blocked host")
        try:
            addr = ipaddress.ip_address(hostname)
            if _is_blocked(addr):
                raise urllib.error.URLError("redirect to non-global IP")
        except ValueError:
            try:
                for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
                    if _is_blocked(ipaddress.ip_address(sockaddr[0])):
                        raise urllib.error.URLError("redirect resolves to non-global IP")
            except socket.gaierror:
                raise urllib.error.URLError("redirect target DNS failure")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# Install SSRF-safe redirect handler globally before trafilatura uses urllib
urllib.request.install_opener(
    urllib.request.build_opener(_SSRFSafeRedirectHandler)
)

# Hard timeout: 15s total (fetch + extract). Prevents hung network stalls.
def _timeout_handler(*_):
    json.dump({"url": "", "status": "timeout", "text": "", "title": "", "date": "", "total_chars": 0, "truncated": False}, sys.stdout)
    sys.stdout.flush()
    sys.exit(0)

signal.signal(signal.SIGALRM, _timeout_handler)
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
            with open(sys.argv[2]) as f:
                url = f.read().strip()
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
            if _is_blocked(addr):
                _error(url, "fetch_failed")
                return
        except ValueError:
            # hostname is a domain — resolve and check all resulting IPs
            try:
                for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
                    resolved = ipaddress.ip_address(sockaddr[0])
                    if _is_blocked(resolved):
                        _error(url, "fetch_failed")
                        return
            except socket.gaierror:
                _error(url, "fetch_failed")
                return
    except Exception:
        _error(url, "fetch_failed")
        return

    try:
        max_chars = int(max_chars_arg)
        if max_chars <= 0:
            max_chars = 3000
    except ValueError:
        max_chars = 3000

    config = use_config()
    config.set("DEFAULT", "DOWNLOAD_TIMEOUT", "10")

    try:
        html = fetch_url(url, config=config)
    except Exception:
        _error(url, "fetch_failed")
        return
    if not html:
        _error(url, "fetch_failed")
        return

    try:
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
    except Exception:
        _error(url, "extraction_failed")
        return

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

    # Quarry sanitization (optional — graceful if binary not found)
    quarry_findings = []
    quarry_bin = os.environ.get("QUARRY_BIN") or shutil.which("quarry")
    if quarry_bin:
        try:
            proc = subprocess.run(
                [quarry_bin, "--profile", "web_page", "--mode", "observe", "--format", "json", "-"],
                input=text,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode in (0, 1, 2) and proc.stdout:
                qr = json.loads(proc.stdout)
                quarry_findings = qr.get("findings", [])
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass  # quarry failed — continue without it

    json.dump({
        "url": url,
        "status": "ok",
        "title": doc.title or "",
        "date": doc.date or "",
        "text": text,
        "total_chars": total_chars,
        "truncated": truncated,
        "quarry_findings": quarry_findings,
    }, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
