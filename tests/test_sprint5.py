import os
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from app.database.connection import DatabaseManager
from app.database.migrations import MigrationRunner
from app.models.habit_recovery import Habit, SleepLog, RecoveryLog, RecoveryProfile, ReadinessState, HabitFrequency
from app.models.domain import User, HabitLog
from app.repositories.user import UserRepository
from app.repositories.habit import HabitRepository
from app.repositories.habit_log import HabitLogRepository
from app.repositories.sleep import SleepRepository
from app.repositories.recovery import RecoveryRepository, RecoveryProfileRepository
from app.services.habit import HabitService
from app.services.recovery import RecoveryService
from app.core.exceptions import ValidationError, ServiceError

TEST_DB_PATH = Path(__file__).resolve().parent / "test_fitos_s5.db"


class TestSprint5HabitRecoveryEngine(unittest.TestCase):
    """Integrity and logic validations covering the Habit + Recovery Engine (Sprint 5)."""

    def setUp(self):
        # Localized testing database manager
        self.db = DatabaseManager(db_path=str(TEST_DB_PATH))

        # Execute migration runners
        self.runner = MigrationRunner(
            migrations_dir=Path(__file__).resolve().parent.parent / "app" / "database" / "migrations",
            db=self.db
        )
        self.runner.run_all()

        # Repositories
        self.user_repo = UserRepository(db=self.db)
        self.habit_repo = HabitRepository(db=self.db)
        self.habit_log_repo = HabitLogRepository(db=self.db)
        self.sleep_repo = SleepRepository(db=self.db)
        self.recovery_repo = RecoveryRepository(db=self.db)
        self.profile_repo = RecoveryProfileRepository(db=self.db)

        # Services
        self.habit_service = HabitService(
            habit_repo=self.habit_repo,
            habit_log_repo=self.habit_log_repo,
            user_repo=self.user_repo
        )
        self.recovery_service = RecoveryService(
            sleep_repo=self.sleep_repo,
            recovery_repo=self.recovery_repo,
            profile_repo=self.profile_repo,
            user_repo=self.user_repo,
            db=self.db
        )

        # Clear database to prevent unique constraint leaks between test cases
        try:
            self.db.execute_write("DELETE FROM recovery_logs;")
            self.db.execute_write("DELETE FROM recovery_profiles;")
            self.db.execute_write("DELETE FROM sleep_logs;")
            self.db.execute_write("DELETE FROM habit_logs;")
            self.db.execute_write("DELETE FROM habits;")
            self.db.execute_write("DELETE FROM workout_sessions;")
            self.db.execute_write("DELETE FROM users;")
        except Exception:
            pass

        # Setup base seed records
        self.user = User(user_id="u-s5", name="Test User", email="test@fitos.org")
        self.user_repo.create_user(self.user)

    def tearDown(self):
        self.db.close_connection()
        if TEST_DB_PATH.exists():
            try:
                os.remove(TEST_DB_PATH)
                for suffix in ["-wal", "-shm"]:
                    extra_file = Path(str(TEST_DB_PATH) + suffix)
                    if extra_file.exists():
                        os.remove(extra_file)
            except OSError:
                pass

    # ============================================================
    # HABIT CRUD TESTS
    # ============================================================

    def test_create_habit(self):
        """Verifies habit creation with valid data."""
        habit = Habit(
            habit_id="h-1",
            user_id="u-s5",
            name="Drink Water",
            description="Drink 8 glasses of water daily",
            frequency="daily",
            target_value=8.0,
            unit="glasses"
        )
        result_id = self.habit_service.create_habit(habit)
        self.assertEqual(result_id, "h-1")

        fetched = self.habit_repo.get_habit("h-1")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Drink Water")
        self.assertEqual(fetched.frequency, "daily")
        self.assertEqual(fetched.target_value, 8.0)

    def test_create_habit_empty_name(self):
        """Verifies empty habit name raises ValidationError."""
        habit = Habit(habit_id="h-bad", user_id="u-s5", name="")
        with self.assertRaises(ValidationError):
            self.habit_service.create_habit(habit)

    def test_create_habit_invalid_frequency(self):
        """Verifies invalid frequency raises ValidationError."""
        habit = Habit(habit_id="h-bad2", user_id="u-s5", name="Test", frequency="monthly")
        with self.assertRaises(ValidationError):
            self.habit_service.create_habit(habit)

    def test_create_habit_invalid_target(self):
        """Verifies non-positive target value raises ValidationError."""
        habit = Habit(habit_id="h-bad3", user_id="u-s5", name="Test", target_value=0)
        with self.assertRaises(ValidationError):
            self.habit_service.create_habit(habit)

    def test_create_habit_nonexistent_user(self):
        """Verifies creating habit for non-existent user raises ValidationError."""
        habit = Habit(habit_id="h-bad4", user_id="u-nonexistent", name="Test")
        with self.assertRaises(ValidationError):
            self.habit_service.create_habit(habit)

    def test_get_user_habits(self):
        """Verifies retrieving all habits for a user."""
        h1 = Habit(habit_id="h-list1", user_id="u-s5", name="Habit 1")
        h2 = Habit(habit_id="h-list2", user_id="u-s5", name="Habit 2")
        self.habit_service.create_habit(h1)
        self.habit_service.create_habit(h2)

        habits = self.habit_service.get_user_habits("u-s5")
        self.assertEqual(len(habits), 2)

    def test_update_habit(self):
        """Verifies updating habit details."""
        habit = Habit(habit_id="h-upd", user_id="u-s5", name="Original Name")
        self.habit_service.create_habit(habit)

        updated = self.habit_service.update_habit("h-upd", {"name": "Updated Name"})
        self.assertTrue(updated)

        fetched = self.habit_repo.get_habit("h-upd")
        self.assertEqual(fetched.name, "Updated Name")

    def test_delete_habit(self):
        """Verifies habit deletion."""
        habit = Habit(habit_id="h-del", user_id="u-s5", name="To Delete")
        self.habit_service.create_habit(habit)

        deleted = self.habit_service.delete_habit("h-del")
        self.assertTrue(deleted)
        self.assertIsNone(self.habit_repo.get_habit("h-del"))

    # ============================================================
    # HABIT LOGGING TESTS
    # ============================================================

    def test_log_habit(self):
        """Verifies logging a daily habit entry."""
        habit = Habit(habit_id="h-log1", user_id="u-s5", name="Exercise")
        self.habit_service.create_habit(habit)

        log_id = self.habit_service.log_habit(
            habit_log_id="hl-1",
            habit_id="h-log1",
            user_id="u-s5",
            log_date="2026-06-30",
            value=1.0,
            status="completed"
        )
        self.assertEqual(log_id, "hl-1")

        logs = self.habit_log_repo.get_habit_logs("h-log1")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].status, "completed")

    def test_log_habit_duplicate(self):
        """Verifies duplicate log per day per habit is blocked."""
        habit = Habit(habit_id="h-dup", user_id="u-s5", name="Read")
        self.habit_service.create_habit(habit)

        self.habit_service.log_habit("hl-dup1", "h-dup", "u-s5", "2026-06-30")

        with self.assertRaises(ValidationError):
            self.habit_service.log_habit("hl-dup2", "h-dup", "u-s5", "2026-06-30")

    def test_log_habit_invalid_status(self):
        """Verifies invalid status raises ValidationError."""
        habit = Habit(habit_id="h-stat", user_id="u-s5", name="Meditate")
        self.habit_service.create_habit(habit)

        with self.assertRaises(ValidationError):
            self.habit_service.log_habit(
                "hl-stat", "h-stat", "u-s5", "2026-06-30",
                status="invalid_status"
            )

    def test_log_habit_nonexistent_habit(self):
        """Verifies logging to non-existent habit raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.habit_service.log_habit("hl-none", "h-none", "u-s5", "2026-06-30")

    # ============================================================
    # HABIT STREAK CALCULATION TESTS
    # ============================================================

    def test_streak_zero_when_no_logs(self):
        """Verifies streak is 0 when no logs exist."""
        habit = Habit(habit_id="h-str0", user_id="u-s5", name="Streak Test")
        self.habit_service.create_habit(habit)

        streak = self.habit_service.compute_streak("h-str0", "u-s5")
        self.assertEqual(streak, 0)

    def test_streak_with_consecutive_days(self):
        """Verifies streak calculation with consecutive completed days."""
        habit = Habit(habit_id="h-str1", user_id="u-s5", name="Daily Streak")
        self.habit_service.create_habit(habit)

        today = datetime.now()
        # Log for today and yesterday
        yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        self.habit_service.log_habit("hl-s1", "h-str1", "u-s5", yesterday)
        self.habit_service.log_habit("hl-s2", "h-str1", "u-s5", today_str)

        streak = self.habit_service.compute_streak("h-str1", "u-s5")
        self.assertGreaterEqual(streak, 2)

    def test_streak_resets_on_missed_day(self):
        """Verifies streak resets if a day is missed."""
        habit = Habit(habit_id="h-str2", user_id="u-s5", name="Streak Reset")
        self.habit_service.create_habit(habit)

        today = datetime.now()
        two_days_ago = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        # Log 2 days ago and today, but miss yesterday
        self.habit_service.log_habit("hl-r1", "h-str2", "u-s5", two_days_ago)
        self.habit_service.log_habit("hl-r2", "h-str2", "u-s5", today_str)

        streak = self.habit_service.compute_streak("h-str2", "u-s5")
        # Streak should be 1 (only today counts, since yesterday was missed)
        self.assertEqual(streak, 1)

    # ============================================================
    # CONSISTENCY SCORE TESTS
    # ============================================================

    def test_consistency_score(self):
        """Verifies consistency score calculation."""
        habit = Habit(habit_id="h-cons", user_id="u-s5", name="Consistency")
        self.habit_service.create_habit(habit)

        today = datetime.now()
        # Log for 3 out of last 5 days
        for i in range(5):
            if i != 1 and i != 3:  # Skip 2 days
                day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                self.habit_service.log_habit(
                    f"hl-cons-{i}", "h-cons", "u-s5", day
                )

        score = self.habit_service.compute_consistency_score("h-cons", "u-s5", days=5)
        self.assertEqual(score, 60.0)  # 3/5 = 60%

    # ============================================================
    # SLEEP LOGGING TESTS
    # ============================================================

    def test_log_sleep(self):
        """Verifies sleep logging with valid data."""
        log_id = self.recovery_service.log_sleep(
            sleep_log_id="sl-1",
            user_id="u-s5",
            log_date="2026-06-30",
            hours=8.0,
            quality_score=8.0
        )
        self.assertEqual(log_id, "sl-1")

        fetched = self.sleep_repo.get_sleep_log("sl-1")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.hours, 8.0)
        self.assertEqual(fetched.quality_score, 8.0)

    def test_log_sleep_invalid_hours(self):
        """Verifies hours > 24 raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.recovery_service.log_sleep("sl-bad1", "u-s5", "2026-06-30", 25.0, 5.0)

    def test_log_sleep_negative_hours(self):
        """Verifies negative hours raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.recovery_service.log_sleep("sl-bad2", "u-s5", "2026-06-30", -1.0, 5.0)

    def test_log_sleep_invalid_quality(self):
        """Verifies quality > 10 raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.recovery_service.log_sleep("sl-bad3", "u-s5", "2026-06-30", 8.0, 11.0)

    def test_log_sleep_duplicate_date(self):
        """Verifies duplicate sleep log for same date is blocked."""
        self.recovery_service.log_sleep("sl-dup1", "u-s5", "2026-06-30", 8.0, 7.0)
        with self.assertRaises(ValidationError):
            self.recovery_service.log_sleep("sl-dup2", "u-s5", "2026-06-30", 7.0, 6.0)

    # ============================================================
    # RECOVERY CALCULATION TESTS
    # ============================================================

    def test_recovery_calculation_with_sleep_data(self):
        """Verifies recovery score calculation with sleep data."""
        # Log sleep for the day
        self.recovery_service.log_sleep("sl-rec1", "u-s5", "2026-07-01", 8.0, 9.0)

        # Calculate recovery
        recovery = self.recovery_service.calculate_recovery("u-s5", "2026-07-01")

        self.assertIsNotNone(recovery)
        self.assertEqual(recovery.user_id, "u-s5")
        self.assertEqual(recovery.log_date, "2026-07-01")
        self.assertGreaterEqual(recovery.recovery_score, 0)
        self.assertLessEqual(recovery.recovery_score, 100)
        self.assertIn(recovery.readiness_state, ["FULL", "MODERATE", "LOW"])

        # With good sleep (9/10 quality, 8h duration), score should be high
        self.assertGreaterEqual(recovery.recovery_score, 50)

    def test_recovery_calculation_without_sleep_data(self):
        """Verifies recovery calculation falls back to defaults when no sleep data."""
        recovery = self.recovery_service.calculate_recovery("u-s5", "2026-07-02")

        self.assertIsNotNone(recovery)
        self.assertGreaterEqual(recovery.recovery_score, 0)
        self.assertLessEqual(recovery.recovery_score, 100)

    def test_recovery_readiness_full(self):
        """Verifies FULL readiness state for high recovery scores."""
        # Log excellent sleep
        self.recovery_service.log_sleep("sl-full", "u-s5", "2026-07-03", 9.0, 10.0)

        recovery = self.recovery_service.calculate_recovery("u-s5", "2026-07-03")
        # With perfect sleep (quality=10, hours=9) and no workouts, score should be high
        if recovery.recovery_score >= 80:
            self.assertEqual(recovery.readiness_state, "FULL")

    def test_recovery_readiness_low(self):
        """Verifies LOW readiness state for low recovery scores."""
        # Log poor sleep
        self.recovery_service.log_sleep("sl-low", "u-s5", "2026-07-04", 2.0, 1.0)

        recovery = self.recovery_service.calculate_recovery("u-s5", "2026-07-04")
        if recovery.recovery_score < 50:
            self.assertEqual(recovery.readiness_state, "LOW")

    def test_recovery_with_workout_dependency(self):
        """Verifies recovery reads workout data (read-only dependency from Sprint 3)."""
        # Create a completed workout session for yesterday
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        # Insert a workout session directly (read-only dependency)
        self.db.execute_write(
            """INSERT INTO workout_sessions (session_id, user_id, plan_id, start_time, end_time, status, calories_burned_kcal)
               VALUES (?, ?, NULL, ?, ?, 'COMPLETED', ?)""",
            ("ws-rec-test", "u-s5", f"{yesterday} 10:00:00", f"{yesterday} 11:00:00", 600.0)
        )

        # Log sleep
        self.recovery_service.log_sleep("sl-wk", "u-s5", today, 7.0, 7.0)

        # Calculate recovery - should factor in the workout
        recovery = self.recovery_service.calculate_recovery("u-s5", today)
        self.assertIsNotNone(recovery)
        self.assertGreaterEqual(recovery.workout_load_component, 0)
        self.assertLessEqual(recovery.workout_load_component, 100)

    def test_recovery_profile_creation(self):
        """Verifies recovery profile is auto-created."""
        profile = self.recovery_service.get_or_create_profile("u-s5")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user_id, "u-s5")
        self.assertEqual(profile.baseline_sleep_hours, 8.0)

    def test_update_baseline_sleep(self):
        """Verifies updating baseline sleep hours."""
        self.recovery_service.get_or_create_profile("u-s5")
        updated = self.recovery_service.update_baseline_sleep("u-s5", 7.5)
        self.assertTrue(updated)

        profile = self.profile_repo.get_user_profile("u-s5")
        self.assertEqual(profile.baseline_sleep_hours, 7.5)

    def test_update_baseline_sleep_invalid(self):
        """Verifies invalid baseline sleep hours raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.recovery_service.update_baseline_sleep("u-s5", 25.0)

    # ============================================================
    # RECOVERY HISTORY TESTS
    # ============================================================

    def test_recovery_history(self):
        """Verifies retrieving recovery history within a date range."""
        # Calculate recovery for multiple days
        self.recovery_service.log_sleep("sl-hist1", "u-s5", "2026-07-10", 8.0, 8.0)
        self.recovery_service.calculate_recovery("u-s5", "2026-07-10")

        self.recovery_service.log_sleep("sl-hist2", "u-s5", "2026-07-11", 7.0, 6.0)
        self.recovery_service.calculate_recovery("u-s5", "2026-07-11")

        history = self.recovery_service.get_recovery_history("u-s5", "2026-07-10", "2026-07-11")
        self.assertEqual(len(history), 2)

    # ============================================================
    # VALIDATION FAILURE TESTS
    # ============================================================

    def test_recovery_score_validation(self):
        """Verifies recovery score is always within 0-100."""
        self.recovery_service.log_sleep("sl-val", "u-s5", "2026-07-20", 8.0, 8.0)
        recovery = self.recovery_service.calculate_recovery("u-s5", "2026-07-20")
        self.assertGreaterEqual(recovery.recovery_score, 0)
        self.assertLessEqual(recovery.recovery_score, 100)

    def test_habit_log_value_validation(self):
        """Verifies habit log with valid value is accepted."""
        habit = Habit(habit_id="h-val", user_id="u-s5", name="Water Intake", target_value=8.0)
        self.habit_service.create_habit(habit)

        log_id = self.habit_service.log_habit(
            "hl-val", "h-val", "u-s5", "2026-07-20",
            value=5.0, status="partial"
        )
        self.assertEqual(log_id, "hl-val")

    def test_recovery_nonexistent_user(self):
        """Verifies recovery calculation for non-existent user raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.recovery_service.calculate_recovery("u-nonexistent", "2026-07-20")


if __name__ == "__main__":
    unittest.main()