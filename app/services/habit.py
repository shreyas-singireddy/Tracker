from datetime import datetime, timedelta

from app.core.exceptions import ServiceError, ValidationError
from app.core.logging import logger
from app.models.domain import HabitLog
from app.models.habit_recovery import Habit
from app.repositories.habit import HabitRepository
from app.repositories.habit_log import HabitLogRepository
from app.repositories.user import UserRepository
from app.utils.validators import (
    validate_habit_frequency,
    validate_habit_log_no_duplicate,
    validate_habit_name,
    validate_habit_target_value,
)


class HabitService:
    """Orchestrates habit tracking, logging, streak calculations, and consistency scoring."""

    def __init__(
        self,
        habit_repo: HabitRepository | None = None,
        habit_log_repo: HabitLogRepository | None = None,
        user_repo: UserRepository | None = None,
    ):
        self.habit_repo = habit_repo or HabitRepository()
        self.habit_log_repo = habit_log_repo or HabitLogRepository()
        self.user_repo = user_repo or UserRepository()

    # --- Habit CRUD ---

    def create_habit(self, habit: Habit) -> str:
        """Validates and creates a new habit."""
        logger.info(f"Creating habit: {habit.name} for user: {habit.user_id}")

        validate_habit_name(habit.name)
        validate_habit_frequency(habit.frequency)
        validate_habit_target_value(habit.target_value)

        # Verify user exists
        if not self.user_repo.get_user(habit.user_id):
            raise ValidationError(f"User with ID {habit.user_id} does not exist.")

        try:
            return self.habit_repo.create_habit(habit)
        except Exception as e:
            logger.error(f"Failed to create habit: {e!s}")
            raise ServiceError("Habit creation failed.", details=str(e))

    def get_user_habits(self, user_id: str) -> list[Habit]:
        """Retrieves all habits for a user."""
        return self.habit_repo.get_user_habits(user_id)

    def get_habit(self, habit_id: str) -> Habit | None:
        """Retrieves a single habit by ID."""
        return self.habit_repo.get_habit(habit_id)

    def update_habit(self, habit_id: str, updates: dict) -> bool:
        """Updates habit details."""
        logger.info(f"Updating habit: {habit_id}")
        rows = self.habit_repo.update_habit(habit_id, updates)
        return rows > 0

    def delete_habit(self, habit_id: str) -> bool:
        """Deletes a habit and its associated logs."""
        logger.info(f"Deleting habit: {habit_id}")
        rows = self.habit_repo.delete_habit(habit_id)
        return rows > 0

    # --- Habit Logging ---

    def log_habit(
        self,
        habit_log_id: str,
        habit_id: str,
        user_id: str,
        log_date: str,
        value: float = 1.0,
        status: str = "completed",
        note: str = "",
    ) -> str:
        """Logs a daily habit entry with duplicate checking."""
        logger.info(f"Logging habit {habit_id} for user {user_id} on {log_date}")

        # Verify habit exists
        habit = self.habit_repo.get_habit(habit_id)
        if not habit:
            raise ValidationError(f"Habit with ID {habit_id} does not exist.")

        # Verify user exists
        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"User with ID {user_id} does not exist.")

        # Ensure no duplicate log per day per habit (business rule)
        validate_habit_log_no_duplicate(habit_id, user_id, log_date, self.habit_log_repo)

        # Validate status
        valid_statuses = ("completed", "missed", "partial")
        if status not in valid_statuses:
            raise ValidationError(
                message="Habit log validation failed: Status must be 'completed', 'missed', or 'partial'.",
                details=f"Received: {status}",
            )

        log = HabitLog(
            habit_log_id=habit_log_id,
            habit_id=habit_id,
            user_id=user_id,
            log_date=log_date,
            value=value,
            status=status,
            note=note,
        )

        try:
            return self.habit_log_repo.create_habit_log(log)
        except Exception as e:
            logger.error(f"Failed to log habit: {e!s}")
            raise ServiceError("Habit logging failed.", details=str(e))

    def get_habit_logs(self, habit_id: str) -> list[HabitLog]:
        """Retrieves all logs for a specific habit."""
        return self.habit_log_repo.get_habit_logs(habit_id)

    def get_user_habit_logs(self, user_id: str) -> list[HabitLog]:
        """Retrieves all habit logs for a user."""
        return self.habit_log_repo.get_user_habit_logs(user_id)

    # --- Streak Calculation ---

    def compute_streak(self, habit_id: str, user_id: str) -> int:
        """Computes the current consecutive-day streak for a habit, resetting on missed days."""
        logger.info(f"Computing streak for habit {habit_id}, user {user_id}")

        habit = self.habit_repo.get_habit(habit_id)
        if not habit:
            raise ValidationError(f"Habit with ID {habit_id} does not exist.")

        # Fetch logs ordered ascending by date
        logs = self.habit_log_repo.get_habit_logs(habit_id)

        # Filter to only this user's logs and sort ascending
        user_logs = [log for log in logs if log.user_id == user_id and log.status == "completed"]
        user_logs.sort(key=lambda x: x.log_date)

        if not user_logs:
            return 0

        # Get unique dates with completed status
        completed_dates = sorted(set(log.log_date for log in user_logs), reverse=True)

        # Check if today or yesterday was completed for active streak
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        if completed_dates[0] != today and completed_dates[0] != yesterday:
            # Streak is broken (most recent completion is older than yesterday)
            return 0

        streak = 0
        current_date = datetime.strptime(completed_dates[0], "%Y-%m-%d")

        for date_str in completed_dates:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            if date == current_date:
                streak += 1
                current_date -= timedelta(days=1)
            elif date < current_date:
                # Gap found — streak broken
                break

        return streak

    # --- Consistency Score ---

    def compute_consistency_score(self, habit_id: str, user_id: str, days: int = 30) -> float:
        """Computes the consistency percentage over a given period."""
        logger.info(f"Computing consistency score for habit {habit_id}, user {user_id}, days {days}")

        habit = self.habit_repo.get_habit(habit_id)
        if not habit:
            raise ValidationError(f"Habit with ID {habit_id} does not exist.")

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

        logs = self.habit_log_repo.get_habit_logs_by_date_range(user_id, start_date, end_date)

        # Filter to only this habit
        habit_logs = [log for log in logs if log.habit_id == habit_id and log.status == "completed"]

        if days <= 0:
            return 0.0

        consistency = (len(habit_logs) / days) * 100.0
        return round(consistency, 2)
