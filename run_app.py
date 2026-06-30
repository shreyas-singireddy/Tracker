#!/usr/bin/env python3
"""FitOS — Application Runner
One-click launch script for the FitOS Offline AI Fitness OS.
Performs DB migration before launching the Streamlit UI.
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    # Ensure we are in the project root
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)

    print("=" * 50)
    print("  FitOS — Offline AI Fitness OS")
    print("=" * 50)

    # Step 1: Boot system & run database migrations
    print("\n[1/2] Booting FitOS System (migrations, modules registry)...")
    try:
        from app.core.bootloader import Bootloader
        Bootloader.boot()
        print("  ✓ System successfully booted.")
    except Exception as e:
        print(f"  ✗ System Boot failed: {e}")
        sys.exit(1)

    # Step 2: Launch Streamlit UI
    print("\n[2/2] Launching FitOS Streamlit UI...")
    ui_path = project_root / "app" / "ui" / "app.py"
    
    if not ui_path.exists():
        print(f"  ✗ UI file not found: {ui_path}")
        sys.exit(1)

    try:
        subprocess.run(["streamlit", "run", str(ui_path)], check=True)
    except FileNotFoundError:
        print("\n  ✗ Streamlit is not installed.")
        print("  Install dependencies with: pip install -r requirements.txt")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\n  ✗ Streamlit exited with error code: {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()