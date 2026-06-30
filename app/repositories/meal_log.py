from typing import Optional, List
from app.repositories.base import BaseRepository
from app.models.domain import MealLog


class MealLogRepository(BaseRepository):
    """Repository class managing CRUD operations for the meal_logs table."""

    def create_meal_log(self, meal_log: MealLog) -> str:
        """Saves a MealLog object to the database."""
        self.create("meal_logs", meal_log.to_dict())
        return meal_log.meal_log_id

    def get_meal_log(self, meal_log_id: str) -> Optional[MealLog]:
        """Fetches a MealLog object by its meal_log_id."""
        row = self.read("meal_logs", "meal_log_id", meal_log_id)
        return MealLog.from_dict(row) if row else None

    def get_user_meal_logs(self, user_id: str) -> List[MealLog]:
        """Retrieves all meal logs registered to a specific user."""
        query = "SELECT * FROM meal_logs WHERE user_id = ? ORDER BY logged_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [MealLog.from_dict(row) for row in rows]

    def update_meal_log(self, meal_log_id: str, updates: dict) -> int:
        """Updates meal log details."""
        return self.update("meal_logs", "meal_log_id", meal_log_id, updates)

    def delete_meal_log(self, meal_log_id: str) -> int:
        """Deletes a meal log record."""
        return self.delete("meal_logs", "meal_log_id", meal_log_id)
