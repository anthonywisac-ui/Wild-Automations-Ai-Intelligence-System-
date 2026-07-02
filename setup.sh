#!/bin/bash
# Wild Automations - Production Setup (Linux / macOS)
# Usage: bash setup.sh

set -e

echo "=== Wild Automations Setup ==="

# 1. Check Python
echo ""
echo "[1/4] Checking Python..."
python3 --version || { echo "ERROR: Python 3 not found"; exit 1; }

# 2. Create venv
echo ""
echo "[2/4] Virtual environment..."
if [ ! -d "venv" ]; then
    echo "Creating venv..."
    python3 -m venv venv
    echo "Created. Activate with: source venv/bin/activate"
else
    echo "venv already exists"
fi

# 3. Install pip packages
echo ""
echo "[3/4] Installing pip packages..."
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -r requirements.txt
echo "Pip packages installed"

# 4. Install Playwright browsers
echo ""
echo "[4/4] Installing Playwright browsers..."
playwright install chromium
echo "Playwright browsers installed"

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Set env vars: cp .env.example .env && edit .env"
echo "  3. Dry run: DRY_RUN=true python main.py"
