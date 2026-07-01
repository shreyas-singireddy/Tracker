from app.models.nutrition import Meal, MealEntry, NutritionLog
from app.repositories.base import BaseRepository


class MealRepository(BaseRepository):
    """CRUD operations for the meals table.

    No business logic. All validation lives in NutritionService.
    Supports filtering by user_id and meal_date.
    """

    def create_meal(self, meal: Meal) -> str:
        """Persists a Meal record and returns its meal_id."""
        self.create("meals", meal.to_dict())
        return meal.meal_id

    def get_meal(self, meal_id: str) -> Meal | None:
        """Fetches a single Meal by primary key."""
        row = self.read("meals", "meal_id", meal_id)
        return Meal.from_dict(row) if row else None

    def get_user_meals(self, user_id: str) -> list[Meal]:
        """Returns all meals for a user, newest first."""
        query = "SELECT * FROM meals WHERE user_id = ? ORDER BY meal_date DESC, created_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [Meal.from_dict(r) for r in rows]

    def get_meals_by_date(self, user_id: str, meal_date: str) -> list[Meal]:
        """Returns all meals for a user on a specific date (YYYY-MM-DD)."""
        query = "SELECT * FROM meals WHERE user_id = ? AND meal_date = ? ORDER BY created_at ASC;"
        rows = self.db.execute_read(query, (user_id, meal_date))
        return [Meal.from_dict(r) for r in rows]

    def get_meal_by_type_and_date(self, user_id: str, meal_type: str, meal_date: str) -> Meal | None:
        """Returns the first meal matching user + type + date (used for duplicate checks)."""
        query = "SELECT * FROM meals WHERE user_id = ? AND meal_type = ? AND meal_date = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id, meal_type, meal_date))
        return Meal.from_dict(row) if row else None

    def update_meal(self, meal_id: str, updates: dict) -> int:
        """Updates meal fields. Returns rows affected."""
        return self.update("meals", "meal_id", meal_id, updates)

    def delete_meal(self, meal_id: str) -> int:
        """Deletes a meal record (cascades to meal_entries). Returns rows affected."""
        return self.delete("meals", "meal_id", meal_id)


class MealEntryRepository(BaseRepository):
    """CRUD operations for the meal_entries table.

    No business logic. Supports filtering by meal_id and food_id lookups.
    """

    def create_entry(self, entry: MealEntry) -> str:
        """Persists a MealEntry record and returns its entry_id."""
        self.create("meal_entries", entry.to_dict())
        return entry.entry_id

    def get_entry(self, entry_id: str) -> MealEntry | None:
        """Fetches a single MealEntry by primary key."""
        row = self.read("meal_entries", "entry_id", entry_id)
        return MealEntry.from_dict(row) if row else None

    def get_meal_entries(self, meal_id: str) -> list[MealEntry]:
        """Returns all food entries within a specific meal, insertion order."""
        query = "SELECT * FROM meal_entries WHERE meal_id = ? ORDER BY created_at ASC;"
        rows = self.db.execute_read(query, (meal_id,))
        return [MealEntry.from_dict(r) for r in rows]

    def get_entry_by_meal_and_food(self, meal_id: str, food_id: str) -> MealEntry | None:
        """Returns an existing entry for the same food in the same meal (duplicate check)."""
        query = "SELECT * FROM meal_entries WHERE meal_id = ? AND food_id = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (meal_id, food_id))
        return MealEntry.from_dict(row) if row else None

    def update_entry(self, entry_id: str, updates: dict) -> int:
        """Updates a meal entry (e.g., to change quantity_g)."""
        return self.update("meal_entries", "entry_id", entry_id, updates)

    def delete_entry(self, entry_id: str) -> int:
        """Deletes a food entry from a meal. Returns rows affected."""
        return self.delete("meal_entries", "entry_id", entry_id)

    def delete_meal_entries(self, meal_id: str) -> int:
        """Removes all food entries belonging to a meal."""
        query = "DELETE FROM meal_entries WHERE meal_id = ?;"
        return self.db.execute_write(query, (meal_id,))


class NutritionLogRepository(BaseRepository):
    """CRUD operations for the nutrition_logs table.

    Supports upsert for daily log records (one row per user per date).
    """

    def create_log(self, log: NutritionLog) -> str:
        """Inserts a new NutritionLog record. Returns log_id."""
        self.create("nutrition_logs", log.to_dict())
        return log.log_id

    def get_log(self, log_id: str) -> NutritionLog | None:
        """Fetches a NutritionLog by primary key."""
        row = self.read("nutrition_logs", "log_id", log_id)
        return NutritionLog.from_dict(row) if row else None

    def get_log_by_date(self, user_id: str, log_date: str) -> NutritionLog | None:
        """Fetches the daily nutrition log for a specific user and date."""
        query = "SELECT * FROM nutrition_logs WHERE user_id = ? AND log_date = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id, log_date))
        return NutritionLog.from_dict(row) if row else None

    def get_user_logs(self, user_id: str) -> list[NutritionLog]:
        """Returns all nutrition log records for a user, newest first."""
        query = "SELECT * FROM nutrition_logs WHERE user_id = ? ORDER BY log_date DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [NutritionLog.from_dict(r) for r in rows]

    def upsert_log(self, log: NutritionLog) -> str:
        """Inserts or replaces the daily nutrition log for a user+date pair.

        Because nutrition_logs has UNIQUE(user_id, log_date), this uses
        INSERT OR REPLACE to handle re-computation on the same date.
        Returns the log_id.
        """
        data = self._filter_fields_by_schema("nutrition_logs", log.to_dict())
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        query = f"INSERT OR REPLACE INTO nutrition_logs ({columns}) VALUES ({placeholders});"
        self.db.execute_write(query, tuple(data.values()))
        return log.log_id

    def delete_log(self, log_id: str) -> int:
        """Deletes a nutrition log record."""
        return self.delete("nutrition_logs", "log_id", log_id)
