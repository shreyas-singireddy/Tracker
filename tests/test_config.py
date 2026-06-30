import os
import unittest
from unittest.mock import patch
from app.core.config import Settings
from app.core.exceptions import ConfigurationError


class TestConfigEnforcement(unittest.TestCase):
    """Verifies that offline enforcement validation rules function correctly on startup."""

    def test_default_offline_mode_is_true(self):
        """Verifies that default settings load in offline mode."""
        settings = Settings()
        self.assertTrue(settings.OFFLINE_MODE)

    def test_disabled_offline_mode_raises_error(self):
        """Verifies that attempting to run FitOS with offline mode disabled raises ConfigurationError."""
        # Use patch to modify environment variables during settings instantiation
        with patch.dict(os.environ, {"OFFLINE_MODE": "False"}):
            with self.assertRaises(ConfigurationError) as context:
                Settings()
            self.assertIn("Offline mode cannot be disabled", str(context.exception))

    def test_settings_properties_exist(self):
        """Verifies that important path settings exist."""
        settings = Settings()
        self.assertIsNotNone(settings.DB_PATH)
        self.assertIsNotNone(settings.LOG_FILE)
        self.assertIsNotNone(settings.LOG_LEVEL)


if __name__ == "__main__":
    unittest.main()
