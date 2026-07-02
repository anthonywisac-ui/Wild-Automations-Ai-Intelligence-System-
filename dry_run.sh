#!/bin/bash
# Dry-run test: validate config, crawl sample portals, skip delivery
# Usage: bash dry_run.sh

set -e

echo "=== Wild Automations Dry-Run Test ==="
echo ""
echo "This will:"
echo "  1. Load and validate bot manifest"
echo "  2. Attempt to crawl configured portals"
echo "  3. Print per-portal stats"
echo "  4. Skip AI processing and delivery"
echo ""

# Check .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env not found"
    echo "Copy .env.example to .env and fill in your values (at least NOTIFY_TO for dry-run)"
    exit 1
fi

# Source .env (optional, for verification only)
# Note: The Python code reads from environment, so .env must be loaded before python runs
# Option 1: Use python-dotenv in the script (recommended)
# Option 2: Load .env manually: export $(cat .env | xargs)

echo "Starting dry-run..."
echo ""

DRY_RUN=true python main.py

echo ""
echo "=== Dry-Run Complete ==="
echo "Check output above for per-portal stats and any validation errors."
echo ""
echo "If all portals crawled successfully (0 items expected since selectors are placeholders),"
echo "the system is ready for:"
echo "  1. Real portal config with verified selectors"
echo "  2. Live database credentials"
echo "  3. Production deployment"
