"""NutritionService — Sprint 4 Nutrition Engine.

Responsibilities:
    A. Food management  (delegates to existing FoodRepository / FoodService)
    B. Meal tracking    (create meal, add/remove entries)
    C. Nutrition calculation (deterministic, formula-only, no AI)

All calculations follow strict scaling rules:
    scale          = quantity_g / food.serving_size_g
    entry_calories = food.calories * scale
    entry_protein  = food.protein  * scale
    entry_carbs    = food.carbs    * scale
    entry_fat      = food.fats     * scale
    daily_total    = sum over all meals on that date
"""

from datetime import datetime, date as date_type
from typing import Dict, List, Optional

from app.models.domain import FoodItem
from app.models.nutrition import Meal, MealEntry, MealType, MacroProfile, NutritionLog
from app.repositories.food import FoodRepository
from app.repositories.nutrition import (
    MealRepository,
    MealEntryRepository,
    NutritionLogRepository,
)
from app.repositories.user import UserRepository
from app.services.food import FoodService
from app.core.exceptions import ValidationError, ServiceError
from app.core.logging import logger
from app.utils.validators import validate_food_item


class NutritionService:
    """Orchestrates the full nutrition engine: food catalog, meal tracking,
    and deterministic macro calculation."""

    def __init__(
        self,
        food_repo: Optional[FoodRepository] = None,
        meal_repo: Optional[MealRepository] = None,
        entry_repo: Optional[MealEntryRepository] = None,
        log_repo: Optional[NutritionLogRepository] = None,
        user_repo: Optional[UserRepository] = None,
        food_service: Optional[FoodService] = None,
    ):
        self.food_repo = food_repo or FoodRepository()
        self.meal_repo = meal_repo or MealRepository()
        self.entry_repo = entry_repo or MealEntryRepository()
        self.log_repo = log_repo or NutritionLogRepository()
        self.user_repo = user_repo or UserRepository()
        self.food_service = food_service or FoodService(food_repo=self.food_repo)

    # ------------------------------------------------------------------ #
    # A. Food Management (delegates to existing FoodService/FoodRepository)
    # ------------------------------------------------------------------ #

    def add_food_item(self, food: FoodItem) -> str:
        """Validates and registers a new food item in the catalog.

        Delegates all validation and persistence to FoodService to avoid duplication.
        """
        return self.food_service.add_food_item(food)

    def update_food_item(self, food_id: str, updates: dict) -> bool:
        """Updates mutable fields of a food item (calories, macros, serving size).

        Validates updated macro fields if present to maintain caloric consistency.
        """
        logger.info(f"Updating food item: {food_id}")

        food = self.food_repo.get_food(food_id)
        if not food:
            raise ValidationError(f"Food item {food_id} not found.")

        # Re-validate macros if any macro field is being changed
        macro_keys = {"calories", "protein", "carbs", "fats"}
        if macro_keys.intersection(updates.keys()):
            new_calories = float(updates.get("calories", food.calories))
            new_protein  = float(updates.get("protein",  food.protein))
            new_carbs    = float(updates.get("carbs",    food.carbs))
            new_fats     = float(updates.get("fats",     food.fats))
            validate_food_item(new_calories, new_protein, new_carbs, new_fats)

        if "serving_size_g" in updates and float(updates["serving_size_g"]) <= 0:
            raise ValidationError("Serving size must be greater than 0 grams.")

        rows = self.food_repo.update_food(food_id, updates)
        return rows > 0

    def get_food_item(self, food_id: str) -> Optional[FoodItem]:
        """Retrieves a single food item by ID."""
        return self.food_repo.get_food(food_id)

    def list_food_database(self) -> List[FoodItem]:
        """Returns the full food catalog."""
        return self.food_repo.list_foods()

    def search_food_by_name(self, name: str) -> List[FoodItem]:
        """Returns all food items whose name contains the search term (case-insensitive)."""
        all_foods = self.food_repo.list_foods()
        term = name.strip().lower()
        return [f for f in all_foods if term in f.name.lower()]

    # ------------------------------------------------------------------ #
    # B. Meal Tracking
    # ------------------------------------------------------------------ #

    def create_meal(self, meal: Meal) -> str:
        """Validates and creates a meal event for a user.

        Validation rules:
            - user must exist
            - meal_type must be one of MealType.ALL
            - meal_date must be YYYY-MM-DD format and not in the future
        """
        logger.info(f"Creating meal: type={meal.meal_type}, date={meal.meal_date}, user={meal.user_id}")

        # Validate user
        if not self.user_repo.get_user(meal.user_id):
            raise ValidationError(f"Cannot create meal: user {meal.user_id} does not exist.")

        # Validate meal type
        if meal.meal_type not in MealType.ALL:
            raise ValidationError(
                message=f"Invalid meal type: '{meal.meal_type}'.",
                details=f"Must be one of: {MealType.ALL}",
            )

        # Validate date format and no-future rule
        self._validate_date_not_future(meal.meal_date)

        try:
            return self.meal_repo.create_meal(meal)
        except Exception as e:
            logger.error(f"Failed to create meal: {e}")
            raise ServiceError("Meal creation failed.", details=str(e))

    def get_meal(self, meal_id: str) -> Optional[Meal]:
        """Returns a single Meal record."""
        return self.meal_repo.get_meal(meal_id)

    def get_meals_for_date(self, user_id: str, meal_date: str) -> List[Meal]:
        """Returns all meal records for a user on a specific date."""
        self._validate_date_format(meal_date)
        return self.meal_repo.get_meals_by_date(user_id, meal_date)

    def delete_meal(self, meal_id: str) -> bool:
        """Deletes a meal and all its entries (via FK CASCADE)."""
        logger.info(f"Deleting meal: {meal_id}")
        rows = self.meal_repo.delete_meal(meal_id)
        return rows > 0

    def add_food_to_meal(self, entry: MealEntry) -> str:
        """Validates and adds a food entry to a meal.

        Validation rules:
            - meal must exist
            - food must exist in catalog
            - quantity_g must be > 0
            - no duplicate (meal_id, food_id) combination
        """
        logger.info(f"Adding food {entry.food_id} to meal {entry.meal_id}, qty={entry.quantity_g}g")

        meal = self.meal_repo.get_meal(entry.meal_id)
        if not meal:
            raise ValidationError(f"Meal {entry.meal_id} does not exist.")

        food = self.food_repo.get_food(entry.food_id)
        if not food:
            raise ValidationError(f"Food item {entry.food_id} does not exist in catalog.")

        if entry.quantity_g <= 0:
            raise ValidationError("Quantity must be greater than 0 grams.")

        # Duplicate check: same food already in this meal
        duplicate = self.entry_repo.get_entry_by_meal_and_food(entry.meal_id, entry.food_id)
        if duplicate:
            raise ValidationError(
                message="This food item is already in the meal.",
                details=f"Existing entry_id: {duplicate.entry_id}. Use update to change quantity.",
            )

        try:
            return self.entry_repo.create_entry(entry)
        except Exception as e:
            logger.error(f"Failed to add food to meal: {e}")
            raise ServiceError("Failed to add food to meal.", details=str(e))

    def update_meal_entry_quantity(self, entry_id: str, new_quantity_g: float) -> bool:
        """Updates the quantity of an existing meal entry."""
        if new_quantity_g <= 0:
            raise ValidationError("Quantity must be greater than 0 grams.")
        entry = self.entry_repo.get_entry(entry_id)
        if not entry:
            raise ValidationError(f"Meal entry {entry_id} not found.")
        rows = self.entry_repo.update_entry(entry_id, {"quantity_g": new_quantity_g})
        return rows > 0

    def remove_food_from_meal(self, entry_id: str) -> bool:
        """Removes a single food entry from a meal."""
        logger.info(f"Removing meal entry: {entry_id}")
        entry = self.entry_repo.get_entry(entry_id)
        if not entry:
            raise ValidationError(f"Meal entry {entry_id} not found.")
        rows = self.entry_repo.delete_entry(entry_id)
        return rows > 0

    def get_meal_entries(self, meal_id: str) -> List[MealEntry]:
        """Returns all food entries for a meal."""
        return self.entry_repo.get_meal_entries(meal_id)

    # ------------------------------------------------------------------ #
    # C. Nutrition Calculations (Deterministic — formula-only, no AI)
    # ------------------------------------------------------------------ #

    def _compute_entry_macros(self, food: FoodItem, quantity_g: float) -> MacroProfile:
        """Scales a food item's per-serving macros to the consumed quantity.

        Formula:
            scale = quantity_g / food.serving_size_g
            macros = food_macro * scale   (for each macro field)
        """
        serving = food.serving_size_g if food.serving_size_g > 0 else 100.0
        scale = quantity_g / serving
        return MacroProfile(
            calories=round(food.calories * scale, 4),
            protein_g=round(food.protein  * scale, 4),
            carbs_g=round(food.carbs     * scale, 4),
            fat_g=round(food.fats        * scale, 4),
            fiber_g=0.0,   # FoodItem does not track fiber/sugar at domain level
            sugar_g=0.0,
        )

    def calculate_meal_macros(self, meal_id: str) -> MacroProfile:
        """Returns the total MacroProfile for all food entries in a meal.

        Computation:
            For each entry in meal:
                scale  = entry.quantity_g / food.serving_size_g
                totals += food_macros * scale
        """
        entries = self.entry_repo.get_meal_entries(meal_id)
        total = MacroProfile()
        for entry in entries:
            food = self.food_repo.get_food(entry.food_id)
            if not food:
                logger.warning(f"Food {entry.food_id} not found during macro calc; skipping.")
                continue
            total = total + self._compute_entry_macros(food, entry.quantity_g)
        return total

    def calculate_daily_macros(self, user_id: str, meal_date: str) -> MacroProfile:
        """Returns the aggregated MacroProfile for ALL meals on a given date.

        Computation:
            daily_total = sum(calculate_meal_macros(meal) for each meal on that date)
        """
        self._validate_date_format(meal_date)
        meals = self.meal_repo.get_meals_by_date(user_id, meal_date)
        daily = MacroProfile()
        for meal in meals:
            daily = daily + self.calculate_meal_macros(meal.meal_id)
        return daily

    def get_nutrition_summary(self, user_id: str, meal_date: str) -> Dict:
        """Returns a structured daily nutrition summary dict with per-meal breakdown.

        Structure:
        {
            "date": "YYYY-MM-DD",
            "meals": [
                {
                    "meal_id": ..., "meal_type": ..., "name": ...,
                    "macros": MacroProfile.to_dict(),
                    "entries": [{"food_id": ..., "quantity_g": ..., "macros": ...}]
                },
                ...
            ],
            "daily_totals": MacroProfile.to_dict()
        }
        """
        self._validate_date_format(meal_date)
        meals = self.meal_repo.get_meals_by_date(user_id, meal_date)
        daily = MacroProfile()
        meals_data = []

        for meal in meals:
            entries = self.entry_repo.get_meal_entries(meal.meal_id)
            meal_total = MacroProfile()
            entries_data = []

            for entry in entries:
                food = self.food_repo.get_food(entry.food_id)
                if not food:
                    continue
                entry_macros = self._compute_entry_macros(food, entry.quantity_g)
                meal_total = meal_total + entry_macros
                entries_data.append({
                    "food_id":    entry.food_id,
                    "food_name":  food.name,
                    "quantity_g": entry.quantity_g,
                    "macros":     entry_macros.to_dict(),
                })

            daily = daily + meal_total
            meals_data.append({
                "meal_id":   meal.meal_id,
                "meal_type": meal.meal_type,
                "name":      meal.name,
                "macros":    meal_total.to_dict(),
                "entries":   entries_data,
            })

        return {
            "date":         meal_date,
            "meals":        meals_data,
            "daily_totals": daily.to_dict(),
        }

    def save_daily_nutrition_log(
        self, log_id: str, user_id: str, meal_date: str
    ) -> NutritionLog:
        """Computes daily macro totals and upserts a NutritionLog record.

        This persists computed totals for reporting. Always reproducible
        by calling calculate_daily_macros() on the same raw meal_entries.
        Returns the saved NutritionLog.
        """
        logger.info(f"Saving daily nutrition log for user={user_id}, date={meal_date}")
        self._validate_date_not_future(meal_date)

        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"User {user_id} does not exist.")

        macros = self.calculate_daily_macros(user_id, meal_date)
        log = NutritionLog(
            log_id=log_id,
            user_id=user_id,
            log_date=meal_date,
            total_calories=round(macros.calories, 4),
            total_protein=round(macros.protein_g, 4),
            total_carbs=round(macros.carbs_g, 4),
            total_fat=round(macros.fat_g, 4),
            total_fiber=round(macros.fiber_g, 4),
            total_sugar=round(macros.sugar_g, 4),
        )

        try:
            self.log_repo.upsert_log(log)
            logger.info(f"Daily nutrition log saved: {log_id}")
            return log
        except Exception as e:
            logger.error(f"Failed to save nutrition log: {e}")
            raise ServiceError("Failed to save daily nutrition log.", details=str(e))

    def get_daily_nutrition_log(self, user_id: str, meal_date: str) -> Optional[NutritionLog]:
        """Returns a previously saved daily NutritionLog, or None if not yet saved."""
        return self.log_repo.get_log_by_date(user_id, meal_date)

    # ------------------------------------------------------------------ #
    # Internal validation helpers
    # ------------------------------------------------------------------ #

    def _validate_date_format(self, date_str: str) -> date_type:
        """Parses YYYY-MM-DD date string, raises ValidationError on failure."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(
                message="Invalid date format. Expected YYYY-MM-DD.",
                details=f"Received: {date_str}",
            )

    def _validate_date_not_future(self, date_str: str) -> None:
        """Validates that a YYYY-MM-DD date is not in the future."""
        parsed = self._validate_date_format(date_str)
        if parsed > date_type.today():
            raise ValidationError(
                message="Date cannot be in the future.",
                details=f"Provided date: {date_str}",
            )
