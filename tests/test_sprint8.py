"""Sprint 8 Verification Test Suite — UI imports & pages.

Verifies that all frontend components and page render entrypoints can be
successfully imported and loaded without syntax errors or broken dependencies.
"""
import unittest

class TestSprint8UI(unittest.TestCase):
    """Verifies that all UI page render entrypoints are structurally sound."""

    def test_ui_imports(self):
        """Verifies that all UI files import without raising any errors."""
        try:
            from app.ui.pages import (
                dashboard,
                workout,
                nutrition,
                habits,
                recovery,
                ai_coach,
                analytics,
                reports,
                settings
            )
            # Assert render attributes exist
            self.assertTrue(callable(dashboard.render))
            self.assertTrue(callable(workout.render))
            self.assertTrue(callable(nutrition.render))
            self.assertTrue(callable(habits.render))
            self.assertTrue(callable(recovery.render))
            self.assertTrue(callable(ai_coach.render))
            self.assertTrue(callable(analytics.render))
            self.assertTrue(callable(reports.render))
            self.assertTrue(callable(settings.render))
        except ImportError as e:
            self.fail(f"Failed to import UI pages: {e}")

    def test_streamlit_app_import(self):
        """Verifies that the main app.py file can be imported without instant side-effects."""
        try:
            import app.ui.app as ui_app
            self.assertTrue(callable(ui_app.run_app))
            self.assertTrue(callable(ui_app.check_db_health))
        except Exception as e:
            self.fail(f"Failed to import app.ui.app: {e}")
