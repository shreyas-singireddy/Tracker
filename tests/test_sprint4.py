"""Sprint 4 Test Suite — Nutrition Engine.

Tests cover:
  1. Food repository CRUD (create, read, update, delete, list)
  2. Meal creation (valid, invalid type, future date, missing user)
  3. Meal entry management (add, duplicate block, quantity validation, remove)
  4. Nutrition calculation (meal macros, daily macros — verified with known inputs)
  5. Validation failures (all boundary cases raise ValidationError)
  6. Daily summary (get_nutrition_summary structure, save_daily_nutrition_log)
"""

import os
import unittest
from datetime import date, timedelta
from pathlib import Path

from app.core.exceptions import ValidationError
from app.database.connection import DatabaseManager
from app.database.migrations import MigrationRunner
from app.models.domain import FoodItem, User
from app.models.nutrition import Meal, MealEntry
from app.repositories.food import FoodRepository
from app.repositories.nutrition import MealEntryRepository, MealRepository, NutritionLogRepository
from app.repositories.user import UserRepository
from app.services.nutrition import NutritionService

TEST_DB_PATH = Path(__file__).resolve().parent / "test_fitos_s4.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "database" / "migrations"

TODAY = date.today().strftime("%Y-%m-%d")
YESTERDAY = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
TOMORROW = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")


class TestSprint4NutritionEngine(unittest.TestCase):
    """Full coverage test class for the Sprint 4 Nutrition Engine module."""

    def setUp(self):
        """Initialise isolated test database and inject all repos/services."""
        self.db = DatabaseManager(db_path=str(TEST_DB_PATH))
        self.runner = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db=self.db)
        self.runner.run_all()

        # Repositories
        self.user_repo = UserRepository(db=self.db)
        self.food_repo = FoodRepository(db=self.db)
        self.meal_repo = MealRepository(db=self.db)
        self.entry_repo = MealEntryRepository(db=self.db)
        self.log_repo = NutritionLogRepository(db=self.db)

        # Clear tables to avoid UNIQUE constraint conflicts across tests
        for table in ("nutrition_logs", "meal_entries", "meals", "users", "foods"):
            try:
                self.db.execute_write(f"DELETE FROM {table};")
            except Exception:
                pass

        # Nutrition service wired to test DB
        self.nutrition = NutritionService(
            food_repo=self.food_repo,
            meal_repo=self.meal_repo,
            entry_repo=self.entry_repo,
            log_repo=self.log_repo,
            user_repo=self.user_repo,
        )

        # Seed: one user, two food items
        self.user = User(user_id="u-n4", name="Nutrition Nadia", email="nadia@fitos.app")
        self.user_repo.create_user(self.user)

        # Chicken breast: 165 kcal / 100g, protein=31g, carbs=0g, fat=3.6g
        self.chicken = FoodItem(
            food_id="f-chicken",
            name="Chicken Breast",
            calories=165.0,
            protein=31.0,
            carbs=0.0,
            fats=3.6,
            serving_size_g=100.0,
        )
        self.food_repo.create_food(self.chicken)

        # Brown rice: 216 kcal / 100g, protein=5g, carbs=45g, fat=1.8g
        self.rice = FoodItem(
            food_id="f-rice",
            name="Brown Rice",
            calories=216.0,
            protein=5.0,
            carbs=45.0,
            fats=1.8,
            serving_size_g=100.0,
        )
        self.food_repo.create_food(self.rice)

    def tearDown(self):
        """Close connection and wipe test database file."""
        self.db.close_connection()
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(TEST_DB_PATH) + suffix) if suffix else TEST_DB_PATH
            if p.exists():
                try:
                    os.remove(p)
                except OSError:
                    pass

    # ------------------------------------------------------------------ #
    # 1. Food Repository CRUD
    # ------------------------------------------------------------------ #

    def test_food_create_and_read(self):
        """Food items can be created and retrieved by ID."""
        retrieved = self.food_repo.get_food("f-chicken")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Chicken Breast")
        self.assertAlmostEqual(retrieved.calories, 165.0)

    def test_food_update(self):
        """Food item calories can be updated."""
        self.food_repo.update_food("f-chicken", {"calories": 170.0})
        updated = self.food_repo.get_food("f-chicken")
        self.assertAlmostEqual(updated.calories, 170.0)

    def test_food_list(self):
        """list_foods returns all seeded foods."""
        foods = self.food_repo.list_foods()
        ids = [f.food_id for f in foods]
        self.assertIn("f-chicken", ids)
        self.assertIn("f-rice", ids)

    def test_food_delete(self):
        """A food item can be deleted."""
        extra = FoodItem(food_id="f-del", name="Delete Me", calories=10.0)
        self.food_repo.create_food(extra)
        self.food_repo.delete_food("f-del")
        self.assertIsNone(self.food_repo.get_food("f-del"))

    def test_food_add_via_service(self):
        """NutritionService.add_food_item validates and persists a new food."""
        apple = FoodItem(
            food_id="f-apple", name="Apple", calories=52.0, protein=0.3, carbs=14.0, fats=0.2, serving_size_g=100.0
        )
        returned_id = self.nutrition.add_food_item(apple)
        self.assertEqual(returned_id, "f-apple")
        self.assertIsNotNone(self.nutrition.get_food_item("f-apple"))

    def test_food_add_duplicate_name_raises(self):
        """Adding a food with the same name raises ValidationError."""
        dup = FoodItem(food_id="f-dup", name="Chicken Breast", calories=165.0)
        with self.assertRaises(ValidationError):
            self.nutrition.add_food_item(dup)

    def test_food_add_negative_calories_raises(self):
        """Food with negative calories raises ValidationError."""
        bad = FoodItem(food_id="f-bad", name="Ghost Food", calories=-10.0)
        with self.assertRaises(ValidationError):
            self.nutrition.add_food_item(bad)

    def test_food_update_via_service(self):
        """NutritionService.update_food_item revalidates macros on update."""
        result = self.nutrition.update_food_item("f-rice", {"calories": 220.0})
        self.assertTrue(result)
        self.assertAlmostEqual(self.food_repo.get_food("f-rice").calories, 220.0)

    def test_food_search_by_name(self):
        """search_food_by_name returns partial case-insensitive matches."""
        results = self.nutrition.search_food_by_name("brown")
        self.assertTrue(any(f.food_id == "f-rice" for f in results))

    # ------------------------------------------------------------------ #
    # 2. Meal Creation
    # ------------------------------------------------------------------ #

    def test_create_meal_valid(self):
        """A valid meal is persisted and retrievable."""
        meal = Meal(meal_id="m-1", user_id="u-n4", meal_type="breakfast", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        fetched = self.meal_repo.get_meal("m-1")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.meal_type, "breakfast")

    def test_create_meal_invalid_type_raises(self):
        """Unknown meal type raises ValidationError."""
        bad_meal = Meal(meal_id="m-bad", user_id="u-n4", meal_type="brunch", meal_date=TODAY)
        with self.assertRaises(ValidationError):
            self.nutrition.create_meal(bad_meal)

    def test_create_meal_future_date_raises(self):
        """Future meal date raises ValidationError."""
        future_meal = Meal(meal_id="m-fut", user_id="u-n4", meal_type="lunch", meal_date=TOMORROW)
        with self.assertRaises(ValidationError):
            self.nutrition.create_meal(future_meal)

    def test_create_meal_invalid_date_format_raises(self):
        """Malformed date string raises ValidationError."""
        bad_date_meal = Meal(meal_id="m-date", user_id="u-n4", meal_type="dinner", meal_date="30-06-2026")
        with self.assertRaises(ValidationError):
            self.nutrition.create_meal(bad_date_meal)

    def test_create_meal_missing_user_raises(self):
        """Creating a meal for a non-existent user raises ValidationError."""
        ghost_meal = Meal(meal_id="m-ghost", user_id="u-ghost", meal_type="snack", meal_date=TODAY)
        with self.assertRaises(ValidationError):
            self.nutrition.create_meal(ghost_meal)

    def test_get_meals_for_date(self):
        """get_meals_for_date returns only meals on the requested date."""
        m1 = Meal(meal_id="m-d1", user_id="u-n4", meal_type="breakfast", meal_date=TODAY)
        m2 = Meal(meal_id="m-d2", user_id="u-n4", meal_type="lunch", meal_date=TODAY)
        m3 = Meal(meal_id="m-d3", user_id="u-n4", meal_type="dinner", meal_date=YESTERDAY)
        for m in (m1, m2, m3):
            self.nutrition.create_meal(m)
        today_meals = self.nutrition.get_meals_for_date("u-n4", TODAY)
        today_ids = [m.meal_id for m in today_meals]
        self.assertIn("m-d1", today_ids)
        self.assertIn("m-d2", today_ids)
        self.assertNotIn("m-d3", today_ids)

    # ------------------------------------------------------------------ #
    # 3. Meal Entry Management
    # ------------------------------------------------------------------ #

    def test_add_food_to_meal_valid(self):
        """A food entry is added and retrievable."""
        meal = Meal(meal_id="m-e1", user_id="u-n4", meal_type="lunch", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        entry = MealEntry(entry_id="e-1", meal_id="m-e1", food_id="f-chicken", quantity_g=150.0)
        self.nutrition.add_food_to_meal(entry)
        entries = self.nutrition.get_meal_entries("m-e1")
        self.assertEqual(len(entries), 1)
        self.assertAlmostEqual(entries[0].quantity_g, 150.0)

    def test_add_duplicate_food_raises(self):
        """Adding the same food twice to the same meal raises ValidationError."""
        meal = Meal(meal_id="m-e2", user_id="u-n4", meal_type="dinner", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        e1 = MealEntry(entry_id="e-a", meal_id="m-e2", food_id="f-rice", quantity_g=200.0)
        e2 = MealEntry(entry_id="e-b", meal_id="m-e2", food_id="f-rice", quantity_g=100.0)
        self.nutrition.add_food_to_meal(e1)
        with self.assertRaises(ValidationError):
            self.nutrition.add_food_to_meal(e2)

    def test_add_food_zero_quantity_raises(self):
        """Quantity of 0 raises ValidationError."""
        meal = Meal(meal_id="m-e3", user_id="u-n4", meal_type="snack", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        bad_entry = MealEntry(entry_id="e-z", meal_id="m-e3", food_id="f-chicken", quantity_g=0.0)
        with self.assertRaises(ValidationError):
            self.nutrition.add_food_to_meal(bad_entry)

    def test_add_food_negative_quantity_raises(self):
        """Negative quantity raises ValidationError."""
        meal = Meal(meal_id="m-e4", user_id="u-n4", meal_type="snack", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        bad_entry = MealEntry(entry_id="e-n", meal_id="m-e4", food_id="f-chicken", quantity_g=-50.0)
        with self.assertRaises(ValidationError):
            self.nutrition.add_food_to_meal(bad_entry)

    def test_add_food_unknown_food_raises(self):
        """Adding a non-existent food item raises ValidationError."""
        meal = Meal(meal_id="m-e5", user_id="u-n4", meal_type="breakfast", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        bad_entry = MealEntry(entry_id="e-unk", meal_id="m-e5", food_id="f-ghost", quantity_g=100.0)
        with self.assertRaises(ValidationError):
            self.nutrition.add_food_to_meal(bad_entry)

    def test_remove_food_from_meal(self):
        """A meal entry can be removed."""
        meal = Meal(meal_id="m-rm", user_id="u-n4", meal_type="lunch", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        entry = MealEntry(entry_id="e-rm", meal_id="m-rm", food_id="f-chicken", quantity_g=100.0)
        self.nutrition.add_food_to_meal(entry)
        self.nutrition.remove_food_from_meal("e-rm")
        self.assertEqual(len(self.nutrition.get_meal_entries("m-rm")), 0)

    def test_update_meal_entry_quantity(self):
        """Meal entry quantity can be updated."""
        meal = Meal(meal_id="m-upd", user_id="u-n4", meal_type="dinner", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        entry = MealEntry(entry_id="e-upd", meal_id="m-upd", food_id="f-rice", quantity_g=100.0)
        self.nutrition.add_food_to_meal(entry)
        self.nutrition.update_meal_entry_quantity("e-upd", 250.0)
        updated = self.entry_repo.get_entry("e-upd")
        self.assertAlmostEqual(updated.quantity_g, 250.0)

    # ------------------------------------------------------------------ #
    # 4. Nutrition Calculation (verified with known inputs)
    # ------------------------------------------------------------------ #

    def test_calculate_meal_macros(self):
        """Meal macro totals are correctly computed from entry quantities.

        Setup:  150g chicken (scale=1.5) + 200g rice (scale=2.0)
        Expected:
            calories = 165*1.5 + 216*2.0 = 247.5 + 432.0 = 679.5
            protein  =  31*1.5 +   5*2.0 =  46.5 +  10.0 =  56.5
            carbs    =   0*1.5 +  45*2.0 =   0.0 +  90.0 =  90.0
            fat      = 3.6*1.5 + 1.8*2.0 =   5.4 +   3.6 =   9.0
        """
        meal = Meal(meal_id="m-calc", user_id="u-n4", meal_type="lunch", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        self.nutrition.add_food_to_meal(
            MealEntry(entry_id="ec-1", meal_id="m-calc", food_id="f-chicken", quantity_g=150.0)
        )
        self.nutrition.add_food_to_meal(
            MealEntry(entry_id="ec-2", meal_id="m-calc", food_id="f-rice", quantity_g=200.0)
        )

        macros = self.nutrition.calculate_meal_macros("m-calc")
        self.assertAlmostEqual(macros.calories, 679.5, places=2)
        self.assertAlmostEqual(macros.protein_g, 56.5, places=2)
        self.assertAlmostEqual(macros.carbs_g, 90.0, places=2)
        self.assertAlmostEqual(macros.fat_g, 9.0, places=2)

    def test_calculate_daily_macros(self):
        """Daily macros aggregate across multiple meals on the same date.

        Setup:
            Breakfast: 100g chicken → calories=165, protein=31, carbs=0, fat=3.6
            Dinner:    100g rice    → calories=216, protein=5,  carbs=45, fat=1.8
        Expected daily:
            calories = 165 + 216 = 381
            protein  =  31 +   5 =  36
            carbs    =   0 +  45 =  45
            fat      = 3.6 + 1.8 = 5.4
        """
        m_b = Meal(meal_id="m-day-b", user_id="u-n4", meal_type="breakfast", meal_date=TODAY)
        m_d = Meal(meal_id="m-day-d", user_id="u-n4", meal_type="dinner", meal_date=TODAY)
        self.nutrition.create_meal(m_b)
        self.nutrition.create_meal(m_d)
        self.nutrition.add_food_to_meal(
            MealEntry(entry_id="ed-1", meal_id="m-day-b", food_id="f-chicken", quantity_g=100.0)
        )
        self.nutrition.add_food_to_meal(
            MealEntry(entry_id="ed-2", meal_id="m-day-d", food_id="f-rice", quantity_g=100.0)
        )

        daily = self.nutrition.calculate_daily_macros("u-n4", TODAY)
        self.assertAlmostEqual(daily.calories, 381.0, places=2)
        self.assertAlmostEqual(daily.protein_g, 36.0, places=2)
        self.assertAlmostEqual(daily.carbs_g, 45.0, places=2)
        self.assertAlmostEqual(daily.fat_g, 5.4, places=2)

    def test_empty_meal_macros_are_zero(self):
        """A meal with no entries returns all-zero MacroProfile."""
        empty_meal = Meal(meal_id="m-emp", user_id="u-n4", meal_type="snack", meal_date=TODAY)
        self.nutrition.create_meal(empty_meal)
        macros = self.nutrition.calculate_meal_macros("m-emp")
        self.assertAlmostEqual(macros.calories, 0.0)
        self.assertAlmostEqual(macros.protein_g, 0.0)

    def test_daily_macros_no_meals_are_zero(self):
        """A day with no meals returns all-zero daily MacroProfile."""
        daily = self.nutrition.calculate_daily_macros("u-n4", YESTERDAY)
        self.assertAlmostEqual(daily.calories, 0.0)

    # ------------------------------------------------------------------ #
    # 5. Daily Summary
    # ------------------------------------------------------------------ #

    def test_get_nutrition_summary_structure(self):
        """get_nutrition_summary returns the expected nested dict structure."""
        meal = Meal(meal_id="m-sum", user_id="u-n4", meal_type="lunch", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        self.nutrition.add_food_to_meal(
            MealEntry(entry_id="es-1", meal_id="m-sum", food_id="f-chicken", quantity_g=100.0)
        )
        summary = self.nutrition.get_nutrition_summary("u-n4", TODAY)

        self.assertIn("date", summary)
        self.assertIn("meals", summary)
        self.assertIn("daily_totals", summary)
        self.assertEqual(summary["date"], TODAY)
        self.assertEqual(len(summary["meals"]), 1)

        meal_entry = summary["meals"][0]
        self.assertIn("meal_id", meal_entry)
        self.assertIn("macros", meal_entry)
        self.assertIn("entries", meal_entry)
        self.assertAlmostEqual(meal_entry["macros"]["calories"], 165.0, places=2)
        self.assertAlmostEqual(summary["daily_totals"]["calories"], 165.0, places=2)

    def test_save_and_retrieve_daily_nutrition_log(self):
        """save_daily_nutrition_log persists totals and get_daily_nutrition_log retrieves them."""
        meal = Meal(meal_id="m-log", user_id="u-n4", meal_type="breakfast", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        self.nutrition.add_food_to_meal(MealEntry(entry_id="el-1", meal_id="m-log", food_id="f-rice", quantity_g=100.0))
        saved = self.nutrition.save_daily_nutrition_log("log-1", "u-n4", TODAY)
        self.assertAlmostEqual(saved.total_calories, 216.0, places=2)

        retrieved = self.nutrition.get_daily_nutrition_log("u-n4", TODAY)
        self.assertIsNotNone(retrieved)
        self.assertAlmostEqual(retrieved.total_calories, 216.0, places=2)
        self.assertAlmostEqual(retrieved.total_carbs, 45.0, places=2)

    def test_save_log_upserts_on_recompute(self):
        """Calling save_daily_nutrition_log twice on the same day upserts (no duplicate error)."""
        meal = Meal(meal_id="m-ups", user_id="u-n4", meal_type="dinner", meal_date=TODAY)
        self.nutrition.create_meal(meal)
        self.nutrition.add_food_to_meal(
            MealEntry(entry_id="eu-1", meal_id="m-ups", food_id="f-chicken", quantity_g=100.0)
        )
        self.nutrition.save_daily_nutrition_log("log-ups", "u-n4", TODAY)
        # Add more food and recompute — should NOT raise a UNIQUE error
        self.nutrition.add_food_to_meal(MealEntry(entry_id="eu-2", meal_id="m-ups", food_id="f-rice", quantity_g=100.0))
        saved = self.nutrition.save_daily_nutrition_log("log-ups", "u-n4", TODAY)
        self.assertAlmostEqual(saved.total_calories, 165.0 + 216.0, places=2)

    def test_save_log_future_date_raises(self):
        """Saving a nutrition log with a future date raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.nutrition.save_daily_nutrition_log("log-fut", "u-n4", TOMORROW)

    def test_save_log_missing_user_raises(self):
        """Saving a nutrition log for an unknown user raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.nutrition.save_daily_nutrition_log("log-ghost", "u-ghost", TODAY)


if __name__ == "__main__":
    unittest.main()
