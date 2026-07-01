from app.models.habit_recovery import Habit
from app.repositories.base import BaseRepository


class HabitRepository(BaseRepository):
    """Repository class managing CRUD operations for the habits table."""

    def create_habit(self, habit: Habit) -> str:
        """Saves a Habit object to the database."""
        self.create("habits", habit.to_dict())
        return habit.habit_id

    def get_habit(self, habit_id: str) -> Habit | None:
        """Fetches a Habit object by ID."""
        row = self.read("habits", "habit_id", habit_id)
        return Habit.from_dict(row) if row else None

    def get_user_habits(self, user_id: str) -> list[Habit]:
        """Retrieves all habits configured for a specific user."""
        query = "SELECT * FROM habits WHERE user_id = ? ORDER BY created_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [Habit.from_dict(row) for row in rows]

    def update_habit(self, habit_id: str, updates: dict) -> int:
        """Updates habit details."""
        return self.update("habits", "habit_id", habit_id, updates)

    def delete_habit(self, habit_id: str) -> int:
        """Deletes a habit record."""
        return self.delete("habits", "habit_id", habit_id)
