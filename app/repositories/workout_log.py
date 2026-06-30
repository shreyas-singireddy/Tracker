from typing import Optional, List
from app.repositories.base import BaseRepository
from app.models.domain import WorkoutLog


class WorkoutLogRepository(BaseRepository):
    """Repository class managing CRUD operations for the workout_logs table."""

    def create_workout_log(self, log: WorkoutLog) -> str:
        """Saves a WorkoutLog object to the database."""
        self.create("workout_logs", log.to_dict())
        return log.log_id

    def get_workout_log(self, log_id: str) -> Optional[WorkoutLog]:
        """Fetches a WorkoutLog object by its log_id."""
        row = self.read("workout_logs", "log_id", log_id)
        return WorkoutLog.from_dict(row) if row else None

    def get_user_workout_logs(self, user_id: str) -> List[WorkoutLog]:
        """Retrieves all workout logs registered to a specific user."""
        query = "SELECT * FROM workout_logs WHERE user_id = ? ORDER BY logged_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [WorkoutLog.from_dict(row) for row in rows]

    def update_workout_log(self, log_id: str, updates: dict) -> int:
        """Updates workout log details."""
        return self.update("workout_logs", "log_id", log_id, updates)

    def delete_workout_log(self, log_id: str) -> int:
        """Deletes a workout log record."""
        return self.delete("workout_logs", "log_id", log_id)
