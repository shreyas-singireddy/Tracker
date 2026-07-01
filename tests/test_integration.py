"""FitOS — Cross-Module Integration Tests
Verifies that all sprints work together correctly.
Tests data flow across modules without modifying any existing code.
"""

import os
import unittest
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from app.core.exceptions import ValidationError
from app.database.connection import DatabaseManager
from app.database.migrations import MigrationRunner
from app.models.domain import FoodItem, User
from app.models.habit_recovery import Habit
from app.models.nutrition import Meal, MealEntry
from app.models.workout import WorkoutPlan
from app.repositories.analytics import (
    AnalyticsSnapshotRepository,
    FitnessScoreRepository,
    ProgressTrendRepository,
    ReportRepository,
)
from app.repositories.exercise import ExerciseRepository
from app.repositories.food import FoodRepository
from app.repositories.habit import HabitRepository
from app.repositories.habit_log import HabitLogRepository
from app.repositories.nutrition import MealEntryRepository, MealRepository, NutritionLogRepository
from app.repositories.recovery import RecoveryProfileRepository, RecoveryRepository
from app.repositories.sleep import SleepRepository
from app.repositories.user import UserRepository
from app.repositories.workout import (
    ExerciseLogRepository,
    ExerciseSetRepository,
    WorkoutPlanRepository,
    WorkoutSessionRepository,
)
from app.services.analytics import AnalyticsService
from app.services.habit import HabitService
from app.services.nutrition import NutritionService
from app.services.recovery import RecoveryService
from app.services.workout import WorkoutService

TEST_DB_DIR = Path(__file__).resolve().parent


class TestCrossModuleIntegration(unittest.TestCase):
    """Verifies data flows correctly across all FitOS modules."""

    def setUp(self):
        # Use a unique DB path per test to avoid WAL/locking issues
        self.test_db_path = TEST_DB_DIR / f"test_fitos_int_{uuid.uuid4().hex[:8]}.db"
        self.db = DatabaseManager(db_path=str(self.test_db_path))
        self.runner = MigrationRunner(
            migrations_dir=Path(__file__).resolve().parent.parent / "app" / "database" / "migrations", db=self.db
        )
        self.runner.run_all()

        # --- Setup Repositories ---
        self.user_repo = UserRepository(db=self.db)
        self.food_repo = FoodRepository(db=self.db)
        self.exercise_repo = ExerciseRepository(db=self.db)
        self.plan_repo = WorkoutPlanRepository(db=self.db)
        self.session_repo = WorkoutSessionRepository(db=self.db)
        self.log_repo = ExerciseLogRepository(db=self.db)
        self.set_repo = ExerciseSetRepository(db=self.db)
        self.meal_repo = MealRepository(db=self.db)
        self.entry_repo = MealEntryRepository(db=self.db)
        self.nutrition_log_repo = NutritionLogRepository(db=self.db)
        self.habit_repo = HabitRepository(db=self.db)
        self.habit_log_repo = HabitLogRepository(db=self.db)
        self.sleep_repo = SleepRepository(db=self.db)
        self.recovery_repo = RecoveryRepository(db=self.db)
        self.score_repo = FitnessScoreRepository(db=self.db)
        self.report_repo = ReportRepository(db=self.db)
        self.profile_repo = RecoveryProfileRepository(db=self.db)

        # --- Setup Services ---
        self.workout_service = WorkoutService(
            plan_repo=self.plan_repo,
            session_repo=self.session_repo,
            log_repo=self.log_repo,
            set_repo=self.set_repo,
            user_repo=self.user_repo,
            exercise_repo=self.exercise_repo,
        )
        self.nutrition_service = NutritionService(
            food_repo=self.food_repo,
            meal_repo=self.meal_repo,
            entry_repo=self.entry_repo,
            log_repo=self.nutrition_log_repo,
            user_repo=self.user_repo,
        )
        self.habit_service = HabitService(
            habit_repo=self.habit_repo, habit_log_repo=self.habit_log_repo, user_repo=self.user_repo
        )
        self.recovery_service = RecoveryService(
            sleep_repo=self.sleep_repo,
            recovery_repo=self.recovery_repo,
            profile_repo=self.profile_repo,
            user_repo=self.user_repo,
            db=self.db,
        )
        self.snapshot_repo = AnalyticsSnapshotRepository(db=self.db)
        self.trend_repo = ProgressTrendRepository(db=self.db)
        self.analytics_service = AnalyticsService(
            score_repo=self.score_repo,
            report_repo=self.report_repo,
            snapshot_repo=self.snapshot_repo,
            trend_repo=self.trend_repo,
            user_repo=self.user_repo,
            workout_session_repo=self.session_repo,
            nutrition_log_repo=self.nutrition_log_repo,
            habit_repo=self.habit_repo,
            habit_log_repo=self.habit_log_repo,
            recovery_repo=self.recovery_repo,
            db=self.db,
        )

        # --- Seed Base Data ---
        self.user = User(user_id="u-int", name="Integration User", email="int@fitos.org")
        self.user_repo.create_user(self.user)

        from app.models.domain import Exercise

        self.exercise_obj = Exercise(
            exercise_id="e-squat-int", name="Barbell Squat", category="strength", form_rules="{}"
        )
        self.exercise_repo.create_exercise(self.exercise_obj)

        self.food = FoodItem(
            food_id="f-chicken-int",
            name="Chicken Breast",
            calories=250.0,
            protein=50.0,
            carbs=0.0,
            fats=5.0,
            serving_size_g=150.0,
        )
        self.food_repo.create_food(self.food)

    def tearDown(self):
        self.db.close_connection()
        if self.test_db_path.exists():
            try:
                os.remove(self.test_db_path)
                for suffix in ["-wal", "-shm"]:
                    extra_file = Path(str(self.test_db_path) + suffix)
                    if extra_file.exists():
                        os.remove(extra_file)
            except OSError:
                pass

    # ================================================================ #
    # FULL USER JOURNEY: Workout → Nutrition → Habits → Recovery → Analytics
    # ================================================================ #

    def test_full_user_journey(self):
        """Simulates a complete user day: workout, eat, log habits, sleep, check analytics."""
        today = datetime.now().strftime("%Y-%m-%d")

        # --- Step 1: Workout (Sprint 3) ---
        plan = WorkoutPlan(plan_id="p-int", user_id="u-int", name="Leg Day", split_name="Legs")
        self.workout_service.create_workout_plan(plan)

        self.workout_service.start_session(session_id="s-int", user_id="u-int", plan_id="p-int")
        self.workout_service.add_exercise_to_session("s-int", "e-squat-int", "el-int")
        self.workout_service.log_set(
            set_id="set-int-1",
            session_id="s-int",
            exercise_log_id="el-int",
            set_number=1,
            weight=100.0,
            reps=5,
            rpe=8.0,
        )
        self.workout_service.log_set(
            set_id="set-int-2",
            session_id="s-int",
            exercise_log_id="el-int",
            set_number=2,
            weight=105.0,
            reps=5,
            rpe=8.5,
        )
        self.workout_service.end_session("s-int", calories_burned=350.0, avg_hr=145)

        # Verify workout data persisted
        session = self.session_repo.get_session("s-int")
        self.assertEqual(session.status, "COMPLETED")
        self.assertEqual(session.calories_burned_kcal, 350.0)

        # --- Step 2: Nutrition (Sprint 4) ---
        meal = Meal(meal_id="m-int", user_id="u-int", meal_type="lunch", meal_date=today, name="Post-workout meal")
        self.nutrition_service.create_meal(meal)

        entry = MealEntry(entry_id="e-int", meal_id="m-int", food_id="f-chicken-int", quantity_g=200.0)
        self.nutrition_service.add_food_to_meal(entry)

        # Calculate macros
        macros = self.nutrition_service.calculate_meal_macros("m-int")
        self.assertGreater(macros.calories, 0)
        self.assertGreater(macros.protein_g, 0)

        # Save daily nutrition log
        log = self.nutrition_service.save_daily_nutrition_log("nl-int", "u-int", today)
        self.assertIsNotNone(log)
        self.assertGreater(log.total_calories, 0)

        # --- Step 3: Habits (Sprint 5) ---
        habit = Habit(habit_id="h-int", user_id="u-int", name="Drink Water", target_value=8.0, unit="glasses")
        self.habit_service.create_habit(habit)

        self.habit_service.log_habit("hl-int", "h-int", "u-int", today, value=6.0, status="completed")

        # Verify streak
        streak = self.habit_service.compute_streak("h-int", "u-int")
        self.assertGreaterEqual(streak, 0)

        # --- Step 4: Sleep & Recovery (Sprint 5) ---
        self.recovery_service.log_sleep("sl-int", "u-int", today, hours=8.0, quality_score=8.0)

        recovery = self.recovery_service.calculate_recovery("u-int", today)
        self.assertIsNotNone(recovery)
        self.assertGreaterEqual(recovery.recovery_score, 0)
        self.assertIn(recovery.readiness_state, ["FULL", "MODERATE", "LOW"])

        # --- Step 5: Analytics (Sprint 7) ---
        score = self.analytics_service.compute_fitness_score("u-int", today)
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score.overall_score, 0)
        self.assertLessEqual(score.overall_score, 100)

        # With workout + nutrition + recovery + habits, score should be meaningful
        self.assertGreater(score.workout_consistency_score, 0)
        self.assertGreater(score.nutrition_score, 0)
        self.assertGreater(score.recovery_score, 0)
        self.assertGreater(score.habits_score, 0)

        # --- Step 6: Weekly Report ---
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
        report = self.analytics_service.generate_weekly_report("u-int", week_start)
        self.assertIsNotNone(report)
        self.assertGreaterEqual(report.total_workouts, 1)
        self.assertGreater(report.avg_fitness_score, 0)

        # --- Step 7: Dashboard Data ---
        dashboard = self.analytics_service.get_dashboard_data("u-int", today)
        self.assertIn("snapshot", dashboard)
        self.assertIn("weekly_report", dashboard)
        self.assertIn("trends", dashboard)

    def test_data_consistency_across_modules(self):
        """Verifies that data written by one module is correctly read by another."""
        today = datetime.now().strftime("%Y-%m-%d")

        # Create a workout session
        self.workout_service.start_session(session_id="s-cons", user_id="u-int")
        self.workout_service.add_exercise_to_session("s-cons", "e-squat-int", "el-cons")
        self.workout_service.log_set("set-cons", "s-cons", "el-cons", 1, 80.0, 8)
        self.workout_service.end_session("s-cons", calories_burned=300.0)

        # Recovery service should read workout data (read-only dependency)
        self.recovery_service.log_sleep("sl-cons", "u-int", today, 7.0, 7.0)
        recovery = self.recovery_service.calculate_recovery("u-int", today)

        # Workout load component should reflect the session
        self.assertGreaterEqual(recovery.workout_load_component, 0)

        # Analytics should aggregate both
        agg = self.analytics_service.get_aggregated_day("u-int", today)
        self.assertEqual(agg["total_workouts"], 1)
        self.assertGreater(agg["calories_burned"], 0)

    def test_empty_state_graceful_handling(self):
        """Verifies all modules handle empty/missing data gracefully."""
        today = "2026-12-25"  # Christmas with no data

        # Analytics with no data
        score = self.analytics_service.compute_fitness_score("u-int", today)
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score.overall_score, 0)
        self.assertLessEqual(score.overall_score, 100)

        # Aggregation with no data
        agg = self.analytics_service.get_aggregated_day("u-int", today)
        self.assertEqual(agg["total_workouts"], 0)
        self.assertEqual(agg["calories_consumed"], 0.0)
        self.assertEqual(agg["recovery_score"], 0.0)

        # Weekly report with no data
        week_start = "2026-12-21"
        report = self.analytics_service.generate_weekly_report("u-int", week_start)
        self.assertIsNotNone(report)
        self.assertEqual(report.total_workouts, 0)

    def test_cross_module_error_propagation(self):
        """Verifies errors propagate correctly across module boundaries."""
        # Non-existent user should fail consistently across all services
        with self.assertRaises(ValidationError):
            self.workout_service.start_session(session_id="s-err", user_id="u-nonexistent")

        with self.assertRaises(ValidationError):
            self.nutrition_service.create_meal(
                Meal(meal_id="m-err", user_id="u-nonexistent", meal_type="lunch", meal_date="2026-01-01")
            )

        with self.assertRaises(ValidationError):
            self.habit_service.create_habit(Habit(habit_id="h-err", user_id="u-nonexistent", name="Test"))

        with self.assertRaises(ValidationError):
            self.recovery_service.log_sleep("sl-err", "u-nonexistent", "2026-01-01", 8.0, 8.0)

        with self.assertRaises(ValidationError):
            self.analytics_service.compute_fitness_score("u-nonexistent", "2026-01-01")


if __name__ == "__main__":
    unittest.main()
