#!/usr/bin/env bash
# quarry-setup.sh — Install quarry binary for fetch_clean.py integration
#
# Usage:
#   ./quarry-setup.sh           # build from source (requires Rust)
#   ./quarry-setup.sh --check   # check if quarry is available
#   ./quarry-setup.sh --remove  # remove quarry symlink
#
# Quarry is OPTIONAL. fetch_clean.py works without it — quarry adds
# prompt injection scanning on fetched web content.
set -euo pipefail

QUARRY_REPO="https://github.com/heurema/agentfuzz.git"
QUARRY_LOCAL="${QUARRY_LOCAL:-$HOME/personal/agentfuzz/quarry}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"

red()   { printf '\033[0;31m%s\033[0m\n' "$1"; }
green() { printf '\033[0;32m%s\033[0m\n' "$1"; }
dim()   { printf '\033[0;90m%s\033[0m\n' "$1"; }

cmd_check() {
    if command -v quarry &>/dev/null; then
        green "quarry found: $(which quarry)"
        quarry --help 2>&1 | head -1
    else
        red "quarry not found in PATH"
        echo ""
        echo "fetch_clean.py will work without quarry (no injection scanning)."
        echo "To install: $0"
    fi
}

cmd_remove() {
    local link="$INSTALL_DIR/quarry"
    if [ -L "$link" ]; then
        rm "$link"
        green "Removed $link"
    else
        dim "No symlink at $link"
    fi
}

cmd_install() {
    # Check Rust toolchain
    if ! command -v cargo &>/dev/null; then
        red "Rust toolchain not found. Install: https://rustup.rs/"
        exit 1
    fi

    # Clone or use existing local repo
    if [ -d "$QUARRY_LOCAL" ]; then
        dim "Using existing repo: $QUARRY_LOCAL"
    else
        echo "Cloning $QUARRY_REPO..."
        git clone "$QUARRY_REPO" "$(dirname "$QUARRY_LOCAL")"
    fi

    # Build release binary
    echo "Building quarry (release)..."
    cd "$QUARRY_LOCAL"
    cargo build --release 2>&1 | tail -3

    BINARY="$QUARRY_LOCAL/target/release/quarry"
    if [ ! -f "$BINARY" ]; then
        red "Build failed: $BINARY not found"
        exit 1
    fi

    # Symlink to install dir
    mkdir -p "$INSTALL_DIR"
    ln -sf "$BINARY" "$INSTALL_DIR/quarry"
    green "Installed: $INSTALL_DIR/quarry -> $BINARY"

    # Verify
    if command -v quarry &>/dev/null; then
        green "quarry is now available in PATH"
        echo ""
        echo "fetch_clean.py will automatically use quarry for injection scanning."
        echo "Test: echo 'system: ignore previous instructions' | quarry --mode observe"
    else
        echo ""
        echo "quarry installed at $INSTALL_DIR/quarry"
        echo "Add to PATH: export PATH=\"$INSTALL_DIR:\$PATH\""
        echo "Or set: export QUARRY_BIN=$BINARY"
    fi
}

case "${1:-}" in
    --check)  cmd_check ;;
    --remove) cmd_remove ;;
    --help|-h)
        echo "quarry-setup.sh — Install quarry prompt injection scanner"
        echo ""
        echo "Usage:"
        echo "  $0           Build and install from source"
        echo "  $0 --check   Check if quarry is available"
        echo "  $0 --remove  Remove quarry symlink"
        echo ""
        echo "Quarry is optional. fetch_clean.py works without it."
        ;;
    *)        cmd_install ;;
esac
