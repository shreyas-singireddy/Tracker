import os
import unittest
from pathlib import Path

from app.core.exceptions import ValidationError
from app.database.connection import DatabaseManager
from app.database.migrations import MigrationRunner
from app.models.domain import Exercise, User
from app.models.workout import WorkoutPlan
from app.repositories.exercise import ExerciseRepository
from app.repositories.user import UserRepository
from app.repositories.workout import (
    ExerciseLogRepository,
    ExerciseSetRepository,
    WorkoutPlanRepository,
    WorkoutSessionRepository,
)
from app.services.workout import WorkoutService

TEST_DB_PATH = Path(__file__).resolve().parent / "test_fitos_s3.db"


class TestSprint3WorkoutEngine(unittest.TestCase):
    """Integrity and logic validations covering the workout session state machine, plans, and sets logging."""

    def setUp(self):
        # Localized testing database manager
        self.db = DatabaseManager(db_path=str(TEST_DB_PATH))

        # Execute migration runners
        self.runner = MigrationRunner(
            migrations_dir=Path(__file__).resolve().parent.parent / "app" / "database" / "migrations", db=self.db
        )
        self.runner.run_all()

        # Repositories
        self.user_repo = UserRepository(db=self.db)
        self.exercise_repo = ExerciseRepository(db=self.db)
        self.plan_repo = WorkoutPlanRepository(db=self.db)
        self.session_repo = WorkoutSessionRepository(db=self.db)
        self.log_repo = ExerciseLogRepository(db=self.db)
        self.set_repo = ExerciseSetRepository(db=self.db)

        # Initialize workout service
        self.workout_service = WorkoutService(
            plan_repo=self.plan_repo,
            session_repo=self.session_repo,
            log_repo=self.log_repo,
            set_repo=self.set_repo,
            user_repo=self.user_repo,
            exercise_repo=self.exercise_repo,
        )

        # Clear database to prevent unique constraint leaks between test cases
        try:
            self.db.execute_write("DELETE FROM users;")
            self.db.execute_write("DELETE FROM exercises;")
        except Exception:
            pass

        # Setup base seed records (User and Exercise)
        self.user = User(user_id="u-s3", name="Sally Jenkins", email="sally@jenkins.org")
        self.user_repo.create_user(self.user)

        self.exercise = Exercise(exercise_id="e-squat", name="Barbell Squat", category="strength", form_rules="{}")
        self.exercise_repo.create_exercise(self.exercise)

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

    def test_create_workout_plan(self):
        """Verifies plan additions and split category checking."""
        # Valid plan
        plan = WorkoutPlan(plan_id="p-1", user_id="u-s3", name="Leg Day", split_name="Legs")
        self.workout_service.create_workout_plan(plan)
        self.assertIsNotNone(self.plan_repo.get_plan("p-1"))

        # Invalid split category
        bad_plan = WorkoutPlan(plan_id="p-2", user_id="u-s3", name="Cardio Burn", split_name="CardioDay")
        with self.assertRaises(ValidationError):
            self.workout_service.create_workout_plan(bad_plan)

        # Empty plan name
        empty_plan = WorkoutPlan(plan_id="p-3", user_id="u-s3", name="", split_name="Push")
        with self.assertRaises(ValidationError):
            self.workout_service.create_workout_plan(empty_plan)

    def test_session_state_machine_flow(self):
        """Verifies transitions from ACTIVE -> PAUSED -> ACTIVE -> COMPLETED, and checks blocking rules."""
        # 1. Start session -> status is ACTIVE
        self.workout_service.start_session(session_id="sess-1", user_id="u-s3")
        session = self.session_repo.get_session("sess-1")
        self.assertEqual(session.status, "ACTIVE")

        # 2. Prevent starting another concurrent session for the same user
        with self.assertRaises(ValidationError):
            self.workout_service.start_session(session_id="sess-2", user_id="u-s3")

        # 3. Transition: ACTIVE -> PAUSED
        self.workout_service.pause_session("sess-1")
        self.assertEqual(self.session_repo.get_session("sess-1").status, "PAUSED")

        # 4. Transition: PAUSED -> ACTIVE
        self.workout_service.resume_session("sess-1")
        self.assertEqual(self.session_repo.get_session("sess-1").status, "ACTIVE")

        # 5. Transition: ACTIVE -> COMPLETED
        self.workout_service.end_session("sess-1", calories_burned=350.0, avg_hr=135)
        session_ended = self.session_repo.get_session("sess-1")
        self.assertEqual(session_ended.status, "COMPLETED")
        self.assertEqual(session_ended.calories_burned_kcal, 350.0)
        self.assertIsNotNone(session_ended.end_time)

        # 6. Asserts error trying to update or alter status of a COMPLETED session
        with self.assertRaises(ValidationError):
            self.workout_service.pause_session("sess-1")

    def test_exercise_logging_and_immutability(self):
        """Verifies exercise set boundary values, duplicates, and session immutability rules."""
        # Start session
        self.workout_service.start_session(session_id="s-active", user_id="u-s3")

        # Add exercise log
        self.workout_service.add_exercise_to_session("s-active", "e-squat", "log-1")
        self.assertIsNotNone(self.log_repo.get_log("log-1"))

        # Block duplicate exercise log in the same session
        with self.assertRaises(ValidationError):
            self.workout_service.add_exercise_to_session("s-active", "e-squat", "log-2")

        # Log Set 1 (Valid)
        self.workout_service.log_set(
            set_id="set-1", session_id="s-active", exercise_log_id="log-1", set_number=1, weight=100.0, reps=5, rpe=8.5
        )
        self.assertIsNotNone(self.set_repo.get_set("set-1"))

        # Validate duplicate set number blocking
        with self.assertRaises(ValidationError):
            self.workout_service.log_set(
                set_id="set-1-dup", session_id="s-active", exercise_log_id="log-1", set_number=1, weight=100.0, reps=5
            )

        # Validate boundary checks: weight < 0
        with self.assertRaises(ValidationError):
            self.workout_service.log_set(
                set_id="set-bad-w", session_id="s-active", exercise_log_id="log-1", set_number=2, weight=-10.0, reps=5
            )

        # Validate boundary checks: reps <= 0
        with self.assertRaises(ValidationError):
            self.workout_service.log_set(
                set_id="set-bad-r", session_id="s-active", exercise_log_id="log-1", set_number=2, weight=100.0, reps=0
            )

        # Validate boundary checks: RPE > 10.0
        with self.assertRaises(ValidationError):
            self.workout_service.log_set(
                set_id="set-bad-rpe",
                session_id="s-active",
                exercise_log_id="log-1",
                set_number=2,
                weight=100.0,
                reps=5,
                rpe=11.0,
            )

        # End session
        self.workout_service.end_session("s-active")

        # Immutability Check: Assert error trying to log set to completed session
        with self.assertRaises(ValidationError):
            self.workout_service.log_set(
                set_id="set-locked", session_id="s-active", exercise_log_id="log-1", set_number=3, weight=100.0, reps=5
            )

        # Immutability Check: Assert error trying to add exercise to completed session
        with self.assertRaises(ValidationError):
            self.workout_service.add_exercise_to_session("s-active", "e-squat", "log-locked")


if __name__ == "__main__":
    unittest.main()
