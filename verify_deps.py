#!/usr/bin/env python3
"""
Verify all dependencies are installed and importable.
Usage: python verify_deps.py
"""

import sys
from typing import Tuple, List

def check_import(module_name: str, pip_name: str = None) -> Tuple[bool, str]:
    """Try to import a module and return (success, message)."""
    pip_name = pip_name or module_name
    try:
        __import__(module_name)
        return True, f"✓ {module_name} OK"
    except ImportError as e:
        return False, f"✗ {module_name} MISSING (pip install {pip_name})"
    except Exception as e:
        return False, f"✗ {module_name} ERROR: {e}"


def main():
    print("=== Wild Automations - Dependency Verification ===\n")

    # Required imports
    required = [
        ("httpx", "httpx"),
        ("openai", "openai"),
        ("supabase", "supabase"),
        ("bs4", "beautifulsoup4"),
    ]

    # Optional imports (with graceful fallbacks)
    optional = [
        ("playwright", "playwright"),
        ("crawl4ai", "crawl4ai"),
        ("scrapling", "scrapling"),
        ("selectolax", "selectolax"),
    ]

    print("REQUIRED:")
    required_ok = True
    for module, pip in required:
        ok, msg = check_import(module, pip)
        print(f"  {msg}")
        if not ok:
            required_ok = False

    print("\nOPTIONAL (graceful fallbacks available):")
    for module, pip in optional:
        ok, msg = check_import(module, pip)
        status = "OPTIONAL" if not ok else ""
        print(f"  {msg} {status}")

    print("\nCore modules:")
    core_mods = ["core.scraper_engine", "core.ai_processor", "core.dedupe_engine", "core.scoring_engine", "core.delivery_engine", "core.database_layer"]
    for mod in core_mods:
        ok, msg = check_import(mod)
        print(f"  {msg}")

    print()
    if required_ok:
        print("✓ All REQUIRED dependencies installed. Ready to run!")
        return 0
    else:
        print("✗ Missing REQUIRED dependencies. Run: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
