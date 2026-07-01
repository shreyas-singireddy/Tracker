"""FitOS Command Line Utility & Initializer Entrypoint."""

import argparse
import os
import subprocess
import sys

from app.core.bootloader import Bootloader
from app.core.logging import logger
from app.database.migrations import migration_runner


def main():
    parser = argparse.ArgumentParser(description="FitOS Command Line Utility")
    parser.add_argument("--init-db", action="store_true", help="Initialize database and run schema migrations")

    args = parser.parse_args()

    if args.init_db:
        print("Initializing FitOS Database...")
        try:
            migration_runner.run_all()
            print("✓ Database initialized successfully.")
            sys.exit(0)
        except Exception as e:
            print(f"✗ Database initialization failed: {e}", file=sys.stderr)
            sys.exit(1)

    # Standard boot & run sequence
    logger.info("Initializing FitOS system configuration...")
    try:
        Bootloader.boot()
    except Exception as e:
        logger.critical(f"Critical error during boot initialization: {e!s}")
        sys.exit(1)

    # Target path for Streamlit application
    ui_app_path = os.path.join("app", "ui", "app.py")
    logger.info("Booting Streamlit UI Shell...")

    try:
        subprocess.run(["streamlit", "run", ui_app_path], check=True)
    except FileNotFoundError:
        logger.error("Streamlit binary not found on the host system PATH.")
        print("\n" + "=" * 50)
        print("FitOS Database migration completed successfully.")
        print("To launch the UI, please ensure Streamlit is installed and run:")
        print(f"streamlit run {ui_app_path}")
        print("=" * 50 + "\n")
    except subprocess.CalledProcessError as e:
        logger.error(f"Streamlit application terminated with exit code: {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
