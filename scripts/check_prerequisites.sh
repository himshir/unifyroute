#!/bin/bash
# UnifyRoute Prerequisite Checker (Shell wrapper for Unix-like systems)
# This wrapper ensures the Python script runs correctly on macOS and Linux

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/check_prerequisites.py"

# Try to find Python 3
if command -v python3 &> /dev/null; then
    exec python3 "$PYTHON_SCRIPT" "$@"
elif command -v python &> /dev/null; then
    exec python "$PYTHON_SCRIPT" "$@"
else
    echo "Error: Python 3 is not installed or not in PATH" >&2
    echo "Please install Python 3.11 or later" >&2
    exit 127
fi
