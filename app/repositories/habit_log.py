from typing import Optional, List
from app.repositories.base import BaseRepository
from app.models.domain import HabitLog


class HabitLogRepository(BaseRepository):
    """Repository class managing CRUD operations for habit logs.

    Sprint 2 created a generic 'habit_logs' table (habit_name, logged_at).
    Sprint 5 introduced a structured 'habit_entries' table (habit_id, log_date).
    The HabitLog domain model was updated to the Sprint 5 schema.
    This repository writes to and reads from 'habit_entries' for all structured
    queries (by habit_id, log_date). The legacy 'habit_logs' table is untouched.
    """

    def create_habit_log(self, log: HabitLog) -> str:
        """Saves a HabitLog object to the habit_entries table."""
        self.create("habit_entries", log.to_dict())
        return log.habit_log_id

    def get_habit_log(self, habit_log_id: str) -> Optional[HabitLog]:
        """Fetches a HabitLog object by its habit_log_id."""
        row = self.read("habit_entries", "habit_log_id", habit_log_id)
        return HabitLog.from_dict(row) if row else None

    def get_user_habit_logs(self, user_id: str) -> List[HabitLog]:
        """Retrieves all habit logs for a specific user, newest first."""
        query = "SELECT * FROM habit_entries WHERE user_id = ? ORDER BY log_date DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [HabitLog.from_dict(row) for row in rows]

    def get_habit_logs_by_date_range(self, user_id: str, start_date: str, end_date: str) -> List[HabitLog]:
        """Retrieves habit logs for a user within a date range."""
        query = "SELECT * FROM habit_entries WHERE user_id = ? AND log_date >= ? AND log_date <= ? ORDER BY log_date ASC;"
        rows = self.db.execute_read(query, (user_id, start_date, end_date))
        return [HabitLog.from_dict(row) for row in rows]

    def get_habit_log_by_date(self, habit_id: str, user_id: str, log_date: str) -> Optional[HabitLog]:
        """Fetches a single habit log by habit_id, user_id and date (for duplicate checking)."""
        query = "SELECT * FROM habit_entries WHERE habit_id = ? AND user_id = ? AND log_date = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (habit_id, user_id, log_date))
        return HabitLog.from_dict(row) if row else None

    def get_habit_logs(self, habit_id: str) -> List[HabitLog]:
        """Retrieves all logs for a specific habit."""
        query = "SELECT * FROM habit_entries WHERE habit_id = ? ORDER BY log_date DESC;"
        rows = self.db.execute_read(query, (habit_id,))
        return [HabitLog.from_dict(row) for row in rows]

    def update_habit_log(self, habit_log_id: str, updates: dict) -> int:
        """Updates habit log details."""
        return self.update("habit_entries", "habit_log_id", habit_log_id, updates)

    def delete_habit_log(self, habit_log_id: str) -> int:
        """Deletes a habit log record."""
        return self.delete("habit_entries", "habit_log_id", habit_log_id)