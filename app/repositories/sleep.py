from typing import Optional, List
from app.repositories.base import BaseRepository
from app.models.habit_recovery import SleepLog


class SleepRepository(BaseRepository):
    """Repository class managing CRUD operations for the sleep_logs table."""

    def create_sleep_log(self, log: SleepLog) -> str:
        """Saves a SleepLog object to the database."""
        self.create("sleep_logs", log.to_dict())
        return log.sleep_log_id

    def get_sleep_log(self, sleep_log_id: str) -> Optional[SleepLog]:
        """Fetches a SleepLog object by ID."""
        row = self.read("sleep_logs", "sleep_log_id", sleep_log_id)
        return SleepLog.from_dict(row) if row else None

    def get_user_sleep_logs(self, user_id: str) -> List[SleepLog]:
        """Retrieves all sleep logs for a specific user."""
        query = "SELECT * FROM sleep_logs WHERE user_id = ? ORDER BY log_date DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [SleepLog.from_dict(row) for row in rows]

    def get_sleep_logs_by_date_range(self, user_id: str, start_date: str, end_date: str) -> List[SleepLog]:
        """Retrieves sleep logs for a user within a date range."""
        query = "SELECT * FROM sleep_logs WHERE user_id = ? AND log_date >= ? AND log_date <= ? ORDER BY log_date ASC;"
        rows = self.db.execute_read(query, (user_id, start_date, end_date))
        return [SleepLog.from_dict(row) for row in rows]

    def get_sleep_log_by_date(self, user_id: str, log_date: str) -> Optional[SleepLog]:
        """Fetches a sleep log by user and date."""
        query = "SELECT * FROM sleep_logs WHERE user_id = ? AND log_date = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id, log_date))
        return SleepLog.from_dict(row) if row else None

    def update_sleep_log(self, sleep_log_id: str, updates: dict) -> int:
        """Updates sleep log details."""
        return self.update("sleep_logs", "sleep_log_id", sleep_log_id, updates)

    def delete_sleep_log(self, sleep_log_id: str) -> int:
        """Deletes a sleep log record."""
        return self.delete("sleep_logs", "sleep_log_id", sleep_log_id)