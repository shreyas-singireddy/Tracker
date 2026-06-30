import os
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from app.database.connection import DatabaseManager
from app.database.migrations import MigrationRunner
from app.models.domain import User, UserProfile, Goal, FoodItem, Exercise, MealLog, WorkoutLog, HabitLog, BodyMeasurement
from app.repositories.user import UserRepository, UserProfileRepository
from app.repositories.goal import GoalRepository
from app.repositories.food import FoodRepository
from app.repositories.exercise import ExerciseRepository
from app.repositories.meal_log import MealLogRepository
from app.repositories.workout_log import WorkoutLogRepository
from app.repositories.habit_log import HabitLogRepository
from app.repositories.body_measurement import BodyMeasurementRepository
from app.services.user import UserService
from app.services.goal import GoalService
from app.services.food import FoodService
from app.services.exercise import ExerciseService
from app.core.exceptions import ValidationError, ServiceError
from app.utils.validators import validate_timestamp

TEST_DB_PATH = Path(__file__).resolve().parent / "test_fitos_s2.db"


class TestSprint2Core(unittest.TestCase):
    """Integrity and validation tests covering database migrations, CRUD, and validations."""

    def setUp(self):
        # Establish localized isolated database context
        self.db = DatabaseManager(db_path=str(TEST_DB_PATH))
        
        self.runner = MigrationRunner(
            migrations_dir=Path(__file__).resolve().parent.parent / "app" / "database" / "migrations",
            db=self.db
        )
        self.runner.run_all()

        # Initialize repositories locked on testing DB
        self.user_repo = UserRepository(db=self.db)
        self.profile_repo = UserProfileRepository(db=self.db)
        self.goal_repo = GoalRepository(db=self.db)
        self.food_repo = FoodRepository(db=self.db)
        self.exercise_repo = ExerciseRepository(db=self.db)
        self.meal_repo = MealLogRepository(db=self.db)
        self.workout_repo = WorkoutLogRepository(db=self.db)
        self.habit_repo = HabitLogRepository(db=self.db)
        self.measure_repo = BodyMeasurementRepository(db=self.db)

        # Initialize services
        self.user_service = UserService(user_repo=self.user_repo, profile_repo=self.profile_repo)
        self.goal_service = GoalService(goal_repo=self.goal_repo, user_repo=self.user_repo)
        self.food_service = FoodService(food_repo=self.food_repo)
        self.exercise_service = ExerciseService(exercise_repo=self.exercise_repo)

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

    def test_database_migration_applied(self):
        """Verifies that all Sprint 2 tables exist in the schema after running migrations."""
        tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = [row["name"] for row in self.db.execute_read(tables_query)]
        
        expected_tables = [
            "schema_migrations", "users", "user_profiles", "goals", 
            "foods", "meal_logs", "habit_logs", "body_measurements", "workout_logs"
        ]
        for tbl in expected_tables:
            self.assertIn(tbl, tables, f"Expected table {tbl} was not created by migrations.")

    def test_repository_crud_operations(self):
        """Verifies CRUD operations on all Sprint 2 tables via Repositories."""
        # 1. Create a User first (required for FK constraints)
        user = User(user_id="usr-100", name="Bob Jenkins", email="bob@jenkins.org")
        self.user_repo.create_user(user)
        self.assertIsNotNone(self.user_repo.get_user("usr-100"))

        # 2. UserProfile CRUD
        profile = UserProfile(user_id="usr-100", birth_date="1990-05-15", weight_kg=78.5, height_cm=182.0)
        self.profile_repo.create_profile(profile)
        self.assertIsNotNone(self.profile_repo.get_profile("usr-100"))

        # 3. Goal CRUD
        goal = Goal(goal_id="g-1", user_id="usr-100", category="weight", target_value=75.0, start_date="2026-06-01")
        self.goal_repo.create_goal(goal)
        self.assertEqual(len(self.goal_repo.get_user_goals("usr-100")), 1)

        # 4. Food CRUD
        food = FoodItem(food_id="f-1", name="Eggs", calories=70.0, protein=6.0, carbs=0.6, fats=5.0)
        self.food_repo.create_food(food)
        self.assertIsNotNone(self.food_repo.get_food("f-1"))

        # 5. MealLog CRUD
        meal = MealLog(meal_log_id="ml-1", user_id="usr-100", food_id="f-1", logged_at="2026-06-30 08:00:00")
        self.meal_repo.create_meal_log(meal)
        self.assertEqual(len(self.meal_repo.get_user_meal_logs("usr-100")), 1)

        # 6. HabitLog CRUD
        # Seed a habits record first (HabitLog now has habit_id FK to habits table)
        self.db.execute_write(
            "INSERT INTO habits (habit_id, user_id, name, frequency) VALUES (?, ?, ?, ?);",
            ("h-1", "usr-100", "Hydration", "daily")
        )
        habit = HabitLog(habit_log_id="hl-1", habit_id="h-1", user_id="usr-100", log_date="2026-06-30", status="completed")
        self.habit_repo.create_habit_log(habit)
        self.assertEqual(len(self.habit_repo.get_user_habit_logs("usr-100")), 1)

        # 7. BodyMeasurement CRUD
        measure = BodyMeasurement(measurement_id="bm-1", user_id="usr-100", weight_kg=78.5, logged_at="2026-06-30 07:00:00")
        self.measure_repo.create_measurement(measure)
        self.assertEqual(len(self.measure_repo.get_user_measurements("usr-100")), 1)

    def test_user_service_validations(self):
        """Verifies age constraints, negative weights/heights, and invalid formatting boundaries."""
        user = User(user_id="usr-test", name="Tester", email="test@test.com")
        
        # Test age < 5
        underage_profile = UserProfile(user_id="usr-test", birth_date="2024-01-01", weight_kg=12.0, height_cm=80.0)
        with self.assertRaises(ValidationError):
            self.user_service.register_user(user, underage_profile)

        # Test age > 100
        overage_profile = UserProfile(user_id="usr-test", birth_date="1900-01-01", weight_kg=60.0, height_cm=160.0)
        with self.assertRaises(ValidationError):
            self.user_service.register_user(user, overage_profile)

        # Test weight <= 0
        weight_profile = UserProfile(user_id="usr-test", birth_date="1990-01-01", weight_kg=0.0, height_cm=170.0)
        with self.assertRaises(ValidationError):
            self.user_service.register_user(user, weight_profile)

        # Test unrealistic height
        height_profile = UserProfile(user_id="usr-test", birth_date="1990-01-01", weight_kg=70.0, height_cm=45.0)
        with self.assertRaises(ValidationError):
            self.user_service.register_user(user, height_profile)

    def test_food_service_macro_consistency(self):
        """Verifies macronutrient caloric calculations match stated calories."""
        # Realistic calorie balance (protein=10g, carbs=15g, fats=2g) -> 10*4 + 15*4 + 2*9 = 118 kcal. Stated = 120
        valid_food = FoodItem(food_id="valid-1", name="Apple Bar", calories=120.0, protein=10.0, carbs=15.0, fats=2.0)
        self.food_service.add_food_item(valid_food)
        self.assertIsNotNone(self.food_repo.get_food("valid-1"))

        # Contradictory calories (Calculated = 118 kcal. Stated = 50 kcal)
        invalid_food = FoodItem(food_id="invalid-1", name="Lying Bar", calories=50.0, protein=10.0, carbs=15.0, fats=2.0)
        with self.assertRaises(ValidationError):
            self.food_service.add_food_item(invalid_food)

    def test_future_timestamp_prevention(self):
        """Verifies that timestamps recorded in the future raise validation errors."""
        future_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        with self.assertRaises(ValidationError):
            validate_timestamp(future_time)


if __name__ == "__main__":
    unittest.main()
