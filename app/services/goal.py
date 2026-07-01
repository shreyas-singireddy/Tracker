from datetime import datetime

from app.core.exceptions import ServiceError, ValidationError
from app.core.logging import logger
from app.models.domain import Goal
from app.repositories.goal import GoalRepository
from app.repositories.user import UserRepository


class GoalService:
    """Orchestrates goal creation and updates while enforcing boundary values and relational rules."""

    def __init__(self, goal_repo: GoalRepository | None = None, user_repo: UserRepository | None = None):
        self.goal_repo = goal_repo or GoalRepository()
        self.user_repo = user_repo or UserRepository()

    def add_goal(self, goal: Goal) -> str:
        """Validates goal thresholds and inserts a new target goal for a verified user."""
        logger.info(f"Adding goal for user: {goal.user_id} in category: {goal.category}")

        # Verify user exists (Data Integrity Rule)
        if not self.user_repo.get_user(goal.user_id):
            logger.warning(f"Goal validation failed: User {goal.user_id} does not exist.")
            raise ValidationError(
                message="Goal validation failed: User account not found.", details=f"User ID: {goal.user_id}"
            )

        # Value boundary validations
        if goal.target_value <= 0:
            raise ValidationError(
                message="Goal target value must be greater than 0.", details=f"Target: {goal.target_value}"
            )

        if goal.category not in ("weight", "steps", "calories", "water", "sleep"):
            raise ValidationError(message="Goal category is invalid.", details=f"Category: {goal.category}")

        # Date validations
        try:
            start = datetime.strptime(goal.start_date, "%Y-%m-%d")
            if goal.target_date:
                target = datetime.strptime(goal.target_date, "%Y-%m-%d")
                if target < start:
                    raise ValidationError(
                        message="Goal timeline is invalid: target date cannot precede start date.",
                        details=f"Start: {goal.start_date}, Target: {goal.target_date}",
                    )
        except ValueError:
            raise ValidationError("Date fields must be formatted as YYYY-MM-DD.")

        # Save to database
        try:
            return self.goal_repo.create_goal(goal)
        except Exception as e:
            logger.error(f"Failed to add goal: {e!s}")
            raise ServiceError("Goal creation failed.", details=str(e))

    def update_goal_progress(self, goal_id: str, current_value: float) -> int:
        """Updates the progress metric for an active goal."""
        logger.info(f"Updating progress for goal: {goal_id} to: {current_value}")

        if current_value < 0:
            raise ValidationError("Progress value cannot be negative.")

        goal = self.goal_repo.get_goal(goal_id)
        if not goal:
            logger.warning(f"Update failed: Goal with ID {goal_id} not found.")
            raise ValidationError(f"Goal with ID {goal_id} does not exist.")

        updates = {"current_value": current_value}
        return self.goal_repo.update_goal(goal_id, updates)
