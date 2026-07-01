from app.models.habit_recovery import RecoveryLog, RecoveryProfile
from app.repositories.base import BaseRepository


class RecoveryRepository(BaseRepository):
    """Repository class managing CRUD operations for recovery_logs table."""

    def create_recovery_log(self, log: RecoveryLog) -> str:
        """Saves a RecoveryLog object to the database."""
        self.create("recovery_logs", log.to_dict())
        return log.recovery_log_id

    def get_recovery_log(self, recovery_log_id: str) -> RecoveryLog | None:
        """Fetches a RecoveryLog object by ID."""
        row = self.read("recovery_logs", "recovery_log_id", recovery_log_id)
        return RecoveryLog.from_dict(row) if row else None

    def get_user_recovery_logs(self, user_id: str) -> list[RecoveryLog]:
        """Retrieves all recovery logs for a specific user."""
        query = "SELECT * FROM recovery_logs WHERE user_id = ? ORDER BY log_date DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [RecoveryLog.from_dict(row) for row in rows]

    def get_recovery_logs_by_date_range(self, user_id: str, start_date: str, end_date: str) -> list[RecoveryLog]:
        """Retrieves recovery logs for a user within a date range."""
        query = (
            "SELECT * FROM recovery_logs WHERE user_id = ? AND log_date >= ? AND log_date <= ? ORDER BY log_date ASC;"
        )
        rows = self.db.execute_read(query, (user_id, start_date, end_date))
        return [RecoveryLog.from_dict(row) for row in rows]

    def get_recovery_log_by_date(self, user_id: str, log_date: str) -> RecoveryLog | None:
        """Fetches a recovery log by user and date."""
        query = "SELECT * FROM recovery_logs WHERE user_id = ? AND log_date = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id, log_date))
        return RecoveryLog.from_dict(row) if row else None

    def update_recovery_log(self, recovery_log_id: str, updates: dict) -> int:
        """Updates recovery log details."""
        return self.update("recovery_logs", "recovery_log_id", recovery_log_id, updates)

    def delete_recovery_log(self, recovery_log_id: str) -> int:
        """Deletes a recovery log record."""
        return self.delete("recovery_logs", "recovery_log_id", recovery_log_id)


class RecoveryProfileRepository(BaseRepository):
    """Repository class managing CRUD operations for recovery_profiles table."""

    def create_profile(self, profile: RecoveryProfile) -> str:
        """Saves a RecoveryProfile object to the database."""
        self.create("recovery_profiles", profile.to_dict())
        return profile.profile_id

    def get_profile(self, profile_id: str) -> RecoveryProfile | None:
        """Fetches a RecoveryProfile object by ID."""
        row = self.read("recovery_profiles", "profile_id", profile_id)
        return RecoveryProfile.from_dict(row) if row else None

    def get_user_profile(self, user_id: str) -> RecoveryProfile | None:
        """Fetches a RecoveryProfile object by user_id."""
        query = "SELECT * FROM recovery_profiles WHERE user_id = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id,))
        return RecoveryProfile.from_dict(row) if row else None

    def update_profile(self, profile_id: str, updates: dict) -> int:
        """Updates recovery profile details."""
        return self.update("recovery_profiles", "profile_id", profile_id, updates)

    def delete_profile(self, profile_id: str) -> int:
        """Deletes a recovery profile record."""
        return self.delete("recovery_profiles", "profile_id", profile_id)
