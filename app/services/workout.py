from datetime import datetime
from typing import Optional, List
from app.repositories.workout import (
    WorkoutPlanRepository,
    WorkoutSessionRepository,
    ExerciseLogRepository,
    ExerciseSetRepository
)
from app.repositories.user import UserRepository
from app.repositories.exercise import ExerciseRepository
from app.models.workout import WorkoutPlan, WorkoutSession, ExerciseLog, ExerciseSet, TrainingSplit
from app.core.exceptions import ValidationError, ServiceError
from app.core.logging import logger
from app.database.connection import db_manager


class WorkoutService:
    """Orchestrates workout planning, session lifecycle state changes, and sets tracking."""

    def __init__(
        self,
        plan_repo: Optional[WorkoutPlanRepository] = None,
        session_repo: Optional[WorkoutSessionRepository] = None,
        log_repo: Optional[ExerciseLogRepository] = None,
        set_repo: Optional[ExerciseSetRepository] = None,
        user_repo: Optional[UserRepository] = None,
        exercise_repo: Optional[ExerciseRepository] = None
    ):
        self.plan_repo = plan_repo or WorkoutPlanRepository()
        self.session_repo = session_repo or WorkoutSessionRepository()
        self.log_repo = log_repo or ExerciseLogRepository()
        self.set_repo = set_repo or ExerciseSetRepository()
        self.user_repo = user_repo or UserRepository()
        self.exercise_repo = exercise_repo or ExerciseRepository()

    # --- Workout Plan Management ---

    def create_workout_plan(self, plan: WorkoutPlan) -> str:
        """Validates split parameters and creates a new workout plan."""
        logger.info(f"Creating workout plan: {plan.name} for user: {plan.user_id}")
        
        if not plan.name.strip():
            raise ValidationError("Workout plan name cannot be empty.")

        # Validate training split category
        valid_splits = [split.value for split in TrainingSplit]
        if plan.split_name not in valid_splits:
            raise ValidationError(
                message="Workout plan creation failed: Invalid training split.",
                details=f"Split: {plan.split_name}. Must be one of: {valid_splits}"
            )

        # Verify user exists (Data Integrity Rule)
        if not self.user_repo.get_user(plan.user_id):
            raise ValidationError(f"User with ID {plan.user_id} does not exist.")

        try:
            return self.plan_repo.create_plan(plan)
        except Exception as e:
            logger.error(f"Failed to create workout plan: {str(e)}")
            raise ServiceError("Workout plan creation failed.", details=str(e))

    def get_user_plans(self, user_id: str) -> List[WorkoutPlan]:
        """Retrieves all plans configured for a user."""
        return self.plan_repo.get_user_plans(user_id)

    def delete_workout_plan(self, plan_id: str) -> bool:
        """Deletes a workout plan."""
        logger.info(f"Deleting workout plan: {plan_id}")
        rows = self.plan_repo.delete_plan(plan_id)
        return rows > 0

    # --- Workout Session Lifecycle ---

    def start_session(self, session_id: str, user_id: str, plan_id: Optional[str] = None) -> str:
        """Transitions user state from NOT_STARTED to ACTIVE and boots a session tracker."""
        logger.info(f"Attempting to start workout session for user: {user_id}")

        # Verify user exists
        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"Cannot start session: User {user_id} does not exist.")

        # Verify plan if provided
        if plan_id and not self.plan_repo.get_plan(plan_id):
            raise ValidationError(f"Cannot start session: Workout plan {plan_id} does not exist.")

        # Business Rule: One active session per user at a time
        active = self.session_repo.get_active_session(user_id)
        if active:
            logger.warning(f"Start rejected: User {user_id} already has an active session: {active.session_id}")
            raise ValidationError(
                message="Cannot start workout session: User already has an active workout session running.",
                details=f"Active session ID: {active.session_id}"
            )

        new_session = WorkoutSession(
            session_id=session_id,
            user_id=user_id,
            plan_id=plan_id,
            start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            end_time=None,
            status="ACTIVE"
        )

        try:
            return self.session_repo.create_session(new_session)
        except Exception as e:
            logger.error(f"Failed to create workout session: {str(e)}")
            raise ServiceError("Failed to start workout session.", details=str(e))

    def pause_session(self, session_id: str) -> None:
        """Transitions state from ACTIVE to PAUSED."""
        logger.info(f"Pausing workout session: {session_id}")
        
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValidationError(f"Workout session {session_id} not found.")

        # State machine transition rule
        if session.status != "ACTIVE":
            raise ValidationError(
                message="Invalid state transition: Can only pause an ACTIVE session.",
                details=f"Current status: {session.status}"
            )

        self.session_repo.update_session(session_id, {"status": "PAUSED"})
        logger.info(f"Session {session_id} paused.")

    def resume_session(self, session_id: str) -> None:
        """Transitions state from PAUSED to ACTIVE."""
        logger.info(f"Resuming workout session: {session_id}")
        
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValidationError(f"Workout session {session_id} not found.")

        # State machine transition rule
        if session.status != "PAUSED":
            raise ValidationError(
                message="Invalid state transition: Can only resume a PAUSED session.",
                details=f"Current status: {session.status}"
            )

        self.session_repo.update_session(session_id, {"status": "ACTIVE"})
        logger.info(f"Session {session_id} resumed.")

    def end_session(self, session_id: str, calories_burned: float = 0.0, avg_hr: Optional[int] = None) -> None:
        """Transitions session to COMPLETED and sets final attributes. COMPLETED is final."""
        logger.info(f"Ending workout session: {session_id}")
        
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValidationError(f"Workout session {session_id} not found.")

        if session.status not in ("ACTIVE", "PAUSED"):
            raise ValidationError(
                message="Invalid state transition: Cannot end a session that is already completed or not started.",
                details=f"Current status: {session.status}"
            )

        if calories_burned < 0:
            raise ValidationError("Calories burned cannot be negative.")
        if avg_hr is not None and avg_hr <= 0:
            raise ValidationError("Average heart rate must be greater than 0.")

        updates = {
            "status": "COMPLETED",
            "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "calories_burned_kcal": calories_burned,
            "avg_heart_rate": avg_hr
        }
        self.session_repo.update_session(session_id, updates)
        logger.info(f"Session {session_id} completed successfully.")

    # --- Exercise Tracking & Set Logging ---

    def add_exercise_to_session(self, session_id: str, exercise_id: str, exercise_log_id: str) -> str:
        """Adds a reference exercise log link inside the active session."""
        logger.info(f"Adding exercise {exercise_id} to session {session_id}")

        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValidationError(f"Session {session_id} does not exist.")

        # Business Rule: Completed sessions are immutable
        if session.status == "COMPLETED":
            raise ValidationError("Cannot modify exercise logs: Workout session is completed.")

        # Verify exercise exists in library
        if not self.exercise_repo.get_exercise(exercise_id):
            raise ValidationError(f"Exercise with ID {exercise_id} not found in catalog.")

        # Verify no duplicate exercise log within the same session
        duplicate = self.log_repo.get_log_by_session_and_exercise(session_id, exercise_id)
        if duplicate:
            raise ValidationError(
                message="Exercise log already exists for this exercise in this session.",
                details=f"Exercise log ID: {duplicate.exercise_log_id}"
            )

        new_log = ExerciseLog(
            exercise_log_id=exercise_log_id,
            session_id=session_id,
            exercise_id=exercise_id
        )

        try:
            return self.log_repo.create_log(new_log)
        except Exception as e:
            logger.error(f"Failed to add exercise log: {str(e)}")
            raise ServiceError("Failed to add exercise to session.", details=str(e))

    def log_set(
        self,
        set_id: str,
        session_id: str,
        exercise_log_id: str,
        set_number: int,
        weight: float,
        reps: int,
        rpe: Optional[float] = None
    ) -> str:
        """Logs a set performance under the exercise log inside an active session."""
        logger.info(f"Logging set {set_number} under log {exercise_log_id}")

        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValidationError(f"Session {session_id} does not exist.")

        # Immutability Check
        if session.status == "COMPLETED":
            raise ValidationError("Cannot log sets: Workout session is completed.")

        # Log confirmation
        log = self.log_repo.get_log(exercise_log_id)
        if not log or log.session_id != session_id:
            raise ValidationError(f"Exercise log {exercise_log_id} does not belong to session {session_id}.")

        # Boundary Validations
        if set_number <= 0:
            raise ValidationError("Set number must be greater than 0.")
        if reps <= 0:
            raise ValidationError("Repetitions must be greater than 0.")
        if weight < 0:
            raise ValidationError("Weight cannot be negative.")
        if rpe is not None and not (1.0 <= rpe <= 10.0):
            raise ValidationError("RPE must be between 1.0 and 10.0.")

        # Check duplicate set number under the exercise log (timestamp + exercise_id duplicate logic)
        duplicate = self.set_repo.get_duplicate_set(exercise_log_id, set_number)
        if duplicate:
            raise ValidationError(
                message="A set record with this set number already exists under this exercise log.",
                details=f"Duplicate Set ID: {duplicate.set_id}"
            )

        new_set = ExerciseSet(
            set_id=set_id,
            session_id=session_id,
            exercise_log_id=exercise_log_id,
            set_number=set_number,
            weight=weight,
            reps=reps,
            rpe=rpe,
            is_completed=False
        )

        try:
            return self.set_repo.create_set(new_set)
        except Exception as e:
            logger.error(f"Failed to create set: {str(e)}")
            raise ServiceError("Failed to log set.", details=str(e))

    def update_set_completion(self, set_id: str, is_completed: bool) -> None:
        """Marks set completion status."""
        logger.info(f"Updating set completion status for: {set_id} to: {is_completed}")
        
        set_obj = self.set_repo.get_set(set_id)
        if not set_obj:
            raise ValidationError(f"Set record {set_id} not found.")

        # Check session immutability
        session = self.session_repo.get_session(set_obj.session_id)
        if session and session.status == "COMPLETED":
            raise ValidationError("Cannot update set: Workout session is completed.")

        self.set_repo.update_set(set_id, {"is_completed": 1 if is_completed else 0})
        logger.info(f"Set {set_id} completion status updated.")
