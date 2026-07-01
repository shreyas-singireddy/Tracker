import os
from pathlib import Path
from typing import Any

from app.core.exceptions import ConfigurationError

# Get project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_env_file(env_path: Path) -> dict[str, str]:
    """Manually parse a simple .env file without external dependencies to maintain offline compatibility."""
    env_vars = {}
    if env_path.exists():
        with env_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip().strip("\"'")
    return env_vars


class Settings:
    """Application settings manager with offline-first validation."""

    def __init__(self, env_file_name: str = ".env"):
        # Load custom .env parameters if present
        env_vars = load_env_file(PROJECT_ROOT / env_file_name)

        # Determine environment
        self.ENV: str = os.getenv("FITOS_ENV", env_vars.get("FITOS_ENV", "development")).lower()

        # Enforce offline mode flag validation
        raw_offline_mode = os.getenv("OFFLINE_MODE", env_vars.get("OFFLINE_MODE", "True"))
        # We parse truthiness
        if raw_offline_mode.lower() not in ("true", "1", "yes"):
            raise ConfigurationError(
                message="Violated Core Architectural Contract: Offline mode cannot be disabled.",
                details=f"Attempted to configure OFFLINE_MODE={raw_offline_mode}. FitOS must run fully offline.",
            )

        self.OFFLINE_MODE: bool = True

        # Database Configuration
        default_db_name = "fitos_test.db" if self.ENV == "testing" else "fitos.db"
        self.DB_PATH: Path = PROJECT_ROOT / os.getenv("DB_PATH", env_vars.get("DB_PATH", default_db_name))

        # Logging Configuration
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", env_vars.get("LOG_LEVEL", "INFO")).upper()
        if self.LOG_LEVEL not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            self.LOG_LEVEL = "INFO"

        self.LOG_FILE: Path = PROJECT_ROOT / os.getenv("LOG_FILE", env_vars.get("LOG_FILE", "logs/fitos.log"))

        # Create log directories if they don't exist
        self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Versioning Design
        self.VERSION: str = "v1.0.0"

        # Explicit Debug Toggle
        self.DEBUG_MODE: bool = (
            self.ENV in ("development", "testing")
            or self.LOG_LEVEL == "DEBUG"
            or os.getenv("DEBUG", env_vars.get("DEBUG", "False")).lower() in ("true", "1", "yes")
        )

        # System-wide Feature Flags (Production toggles)
        self.FEATURE_AI_COACH: bool = os.getenv(
            "FEATURE_AI_COACH", env_vars.get("FEATURE_AI_COACH", "True")
        ).lower() in ("true", "1", "yes")
        self.FEATURE_ANALYTICS: bool = os.getenv(
            "FEATURE_ANALYTICS", env_vars.get("FEATURE_ANALYTICS", "True")
        ).lower() in ("true", "1", "yes")
        self.FEATURE_REPORTS: bool = os.getenv("FEATURE_REPORTS", env_vars.get("FEATURE_REPORTS", "True")).lower() in (
            "true",
            "1",
            "yes",
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Fetch custom config settings safely."""
        return getattr(self, key, default)


# Global settings instance
settings = Settings()
