from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from app.repositories.sleep import SleepRepository
from app.repositories.recovery import RecoveryRepository, RecoveryProfileRepository
from app.repositories.user import UserRepository
from app.models.habit_recovery import SleepLog, RecoveryLog, RecoveryProfile, ReadinessState
from app.core.exceptions import ValidationError, ServiceError
from app.core.logging import logger
from app.utils.validators import (
    validate_sleep_hours,
    validate_sleep_quality,
    validate_recovery_score
)
from app.database.connection import DatabaseManager, db_manager


# Weight constants for recovery score formula
SLEEP_QUALITY_WEIGHT = 0.40
SLEEP_DURATION_WEIGHT = 0.30
WORKOUT_LOAD_WEIGHT = 0.20
REST_DAYS_WEIGHT = 0.10

# Default baseline
DEFAULT_BASELINE_SLEEP_HOURS = 8.0


class RecoveryService:
    """Orchestrates sleep logging, recovery calculation, and readiness state determination."""

    def __init__(
        self,
        sleep_repo: Optional[SleepRepository] = None,
        recovery_repo: Optional[RecoveryRepository] = None,
        profile_repo: Optional[RecoveryProfileRepository] = None,
        user_repo: Optional[UserRepository] = None,
        db: Optional[DatabaseManager] = None
    ):
        self.sleep_repo = sleep_repo or SleepRepository()
        self.recovery_repo = recovery_repo or RecoveryRepository()
        self.profile_repo = profile_repo or RecoveryProfileRepository()
        self.user_repo = user_repo or UserRepository()
        self.db = db or db_manager

    # --- Sleep Logging ---

    def log_sleep(
        self,
        sleep_log_id: str,
        user_id: str,
        log_date: str,
        hours: float,
        quality_score: float
    ) -> str:
        """Validates and logs daily sleep data."""
        logger.info(f"Logging sleep for user {user_id} on {log_date}: {hours}h, quality {quality_score}")

        # Validate inputs
        validate_sleep_hours(hours)
        validate_sleep_quality(quality_score)

        # Verify user exists
        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"User with ID {user_id} does not exist.")

        # Check if a sleep log already exists for this date
        existing = self.sleep_repo.get_sleep_log_by_date(user_id, log_date)
        if existing:
            raise ValidationError(
                message="Sleep log already exists for this date. Use update instead.",
                details=f"User: {user_id}, Date: {log_date}"
            )

        sleep_log = SleepLog(
            sleep_log_id=sleep_log_id,
            user_id=user_id,
            log_date=log_date,
            hours=hours,
            quality_score=quality_score
        )

        try:
            return self.sleep_repo.create_sleep_log(sleep_log)
        except Exception as e:
            logger.error(f"Failed to log sleep: {str(e)}")
            raise ServiceError("Sleep logging failed.", details=str(e))

    def get_sleep_logs(self, user_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[SleepLog]:
        """Retrieves sleep logs for a user, optionally filtered by date range."""
        if start_date and end_date:
            return self.sleep_repo.get_sleep_logs_by_date_range(user_id, start_date, end_date)
        return self.sleep_repo.get_user_sleep_logs(user_id)

    # --- Recovery Profile ---

    def get_or_create_profile(self, user_id: str) -> RecoveryProfile:
        """Retrieves or creates a recovery profile for the user."""
        profile = self.profile_repo.get_user_profile(user_id)
        if profile:
            return profile

        # Create default profile
        import uuid
        profile = RecoveryProfile(
            profile_id=str(uuid.uuid4()),
            user_id=user_id,
            baseline_sleep_hours=DEFAULT_BASELINE_SLEEP_HOURS
        )
        self.profile_repo.create_profile(profile)
        return profile

    def update_baseline_sleep(self, user_id: str, baseline_hours: float) -> bool:
        """Updates the user's baseline sleep hours target."""
        validate_sleep_hours(baseline_hours)

        profile = self.get_or_create_profile(user_id)
        rows = self.profile_repo.update_profile(profile.profile_id, {"baseline_sleep_hours": baseline_hours})
        return rows > 0

    # --- Recovery Score Calculation (Deterministic Formula) ---

    def calculate_recovery(self, user_id: str, log_date: str) -> RecoveryLog:
        """Computes the deterministic recovery score and readiness state for a given date."""
        logger.info(f"Calculating recovery for user {user_id} on {log_date}")

        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"User with ID {user_id} does not exist.")

        profile = self.get_or_create_profile(user_id)
        baseline_hours = profile.baseline_sleep_hours

        # --- Component 1: Sleep Quality (40%) ---
        sleep_log = self.sleep_repo.get_sleep_log_by_date(user_id, log_date)
        if sleep_log:
            # Scale quality_score (0-10) to 0-100
            sleep_quality_component = (sleep_log.quality_score / 10.0) * 100.0
            # Actual sleep duration factor
            hours = sleep_log.hours
        else:
            # No sleep data: neutral assumptions (50% quality, 6h default)
            sleep_quality_component = 50.0
            hours = 6.0

        # --- Component 2: Sleep Duration (30%) ---
        # Actual hours / target hours, clamped at 1.0, scaled × 100
        duration_ratio = min(hours / baseline_hours, 1.0)
        sleep_duration_component = duration_ratio * 100.0

        # --- Component 3: Workout Load (20%) ---
        # Read from workout_sessions to compute recent 3-day workout volume
        workout_load_component = self._compute_workout_load_component(user_id, log_date)

        # --- Component 4: Rest Days (10%) ---
        rest_days_component = self._compute_rest_days_component(user_id, log_date)

        # --- Final Recovery Score ---
        recovery_score = (
            (sleep_quality_component * SLEEP_QUALITY_WEIGHT) +
            (sleep_duration_component * SLEEP_DURATION_WEIGHT) +
            (workout_load_component * WORKOUT_LOAD_WEIGHT) +
            (rest_days_component * REST_DAYS_WEIGHT)
        )
        recovery_score = round(max(0.0, min(100.0, recovery_score)), 2)

        # Determine readiness state
        if recovery_score >= 80:
            readiness_state = ReadinessState.FULL.value
        elif recovery_score >= 50:
            readiness_state = ReadinessState.MODERATE.value
        else:
            readiness_state = ReadinessState.LOW.value

        validate_recovery_score(recovery_score)

        # Check if a recovery log already exists for this date (update or create)
        existing = self.recovery_repo.get_recovery_log_by_date(user_id, log_date)
        recovery_log = RecoveryLog(
            recovery_log_id=existing.recovery_log_id if existing else f"rec-{user_id}-{log_date}",
            user_id=user_id,
            log_date=log_date,
            recovery_score=recovery_score,
            readiness_state=readiness_state,
            sleep_quality_component=round(sleep_quality_component, 2),
            sleep_duration_component=round(sleep_duration_component, 2),
            workout_load_component=round(workout_load_component, 2),
            rest_days_component=round(rest_days_component, 2)
        )

        try:
            if existing:
                self.recovery_repo.update_recovery_log(existing.recovery_log_id, recovery_log.to_dict())
            else:
                self.recovery_repo.create_recovery_log(recovery_log)
        except Exception as e:
            logger.error(f"Failed to save recovery log: {str(e)}")
            raise ServiceError("Recovery calculation failed.", details=str(e))

        return recovery_log

    def _compute_workout_load_component(self, user_id: str, log_date: str) -> float:
        """Computes workout load factor based on last 3 days' workout sessions.

        Uses data from workout_sessions in Sprint 3 (read-only).
        Higher recent workout volume = lower recovery contribution.
        Normalizes: 0 volume = 100 (full rest), high volume = scaled down.
        """
        try:
            log_date_dt = datetime.strptime(log_date, "%Y-%m-%d")
            start_date = (log_date_dt - timedelta(days=3)).strftime("%Y-%m-%d")

            # Query workout_sessions for completed sessions in the last 3 days
            query = """
                SELECT COUNT(*) as session_count,
                       COALESCE(SUM(calories_burned_kcal), 0) as total_calories
                FROM workout_sessions
                WHERE user_id = ? AND status = 'COMPLETED'
                  AND start_time >= ? AND start_time < ?
            """
            next_date = (log_date_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            rows = self.db.execute_read(query, (user_id, start_date, next_date))

            if not rows:
                return 100.0  # No workout data -> full recovery contribution

            row = rows[0]
            session_count = row.get("session_count", 0) or 0
            total_calories = row.get("total_calories", 0) or 0.0

            if session_count == 0:
                return 100.0  # No sessions = full rest contribution

            # Normalize: more sessions/calories = lower score
            # Scale: 0 sessions = 100, 1 session = 70, 2 sessions = 40, 3+ sessions = 20
            if session_count >= 3:
                return 20.0
            elif session_count == 2:
                return 40.0
            elif session_count == 1:
                # Adjust by calories: high calories (>500) = lower recovery
                if total_calories > 500:
                    return 50.0
                return 70.0
            return 100.0

        except Exception as e:
            logger.warning(f"Failed to compute workout load component: {str(e)}")
            return 100.0  # Default to full recovery contribution on error

    def _compute_rest_days_component(self, user_id: str, log_date: str) -> float:
        """Computes rest day factor.

        Rules:
        - No workout today & no workout yesterday -> 100 (full rest)
        - No workout today but workout yesterday -> 50 (moderate rest)
        - Workout today -> 0 (consecutive workout days)
        """
        try:
            log_date_dt = datetime.strptime(log_date, "%Y-%m-%d")
            today_start = log_date
            today_end = (log_date_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            yesterday_start = (log_date_dt - timedelta(days=1)).strftime("%Y-%m-%d")

            # Check if there's a workout today
            query_today = """
                SELECT COUNT(*) as count FROM workout_sessions
                WHERE user_id = ? AND status = 'COMPLETED'
                  AND start_time >= ? AND start_time < ?
            """
            today_rows = self.db.execute_read(query_today, (user_id, today_start, today_end))
            today_count = today_rows[0].get("count", 0) if today_rows else 0

            if today_count > 0:
                # Worked out today = consecutive workout day
                return 0.0

            # Check if there was a workout yesterday
            query_yesterday = """
                SELECT COUNT(*) as count FROM workout_sessions
                WHERE user_id = ? AND status = 'COMPLETED'
                  AND start_time >= ? AND start_time < ?
            """
            yesterday_rows = self.db.execute_read(query_yesterday, (user_id, yesterday_start, today_start))
            yesterday_count = yesterday_rows[0].get("count", 0) if yesterday_rows else 0

            if yesterday_count > 0:
                # No workout today, but workout yesterday = moderate rest
                return 50.0

            # No workout today or yesterday = full rest
            return 100.0

        except Exception as e:
            logger.warning(f"Failed to compute rest days component: {str(e)}")
            return 50.0  # Default to moderate rest on error

    def get_recovery(self, user_id: str, log_date: str) -> Optional[RecoveryLog]:
        """Retrieves the recovery log for a user on a specific date."""
        return self.recovery_repo.get_recovery_log_by_date(user_id, log_date)

    def get_recovery_history(self, user_id: str, start_date: str, end_date: str) -> List[RecoveryLog]:
        """Retrieves recovery history for a user within a date range."""
        return self.recovery_repo.get_recovery_logs_by_date_range(user_id, start_date, end_date)