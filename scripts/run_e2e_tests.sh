#!/bin/bash

# Exit on error
set -e

echo "====================================================="
echo "🛠️  Setting up E2E Test Environment"
echo "====================================================="

# Base directory of the repository
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$DIR/.venv_e2e"

cd "$DIR"

# 1. Create a dedicated VENV for tests
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating a dedicated virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "✅ Virtual environment already exists at $VENV_DIR."
fi

# 2. Activate the virtual environment
source "$VENV_DIR/bin/activate"

# 3. Upgrade pip and install required dependencies
echo "🚀 Installing dependencies (httpx)..."
pip install --upgrade pip -q
pip install httpx -q

echo "✅ Dependencies installed."
echo ""

# 4. Run the test script, passing all arguments provided to this script
python test_api.py "$@"

echo "====================================================="
echo "🎉 E2E Test Run Finished"
echo "====================================================="
