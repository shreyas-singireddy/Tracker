import json

from app.core.exceptions import ServiceError, ValidationError
from app.core.logging import logger
from app.models.domain import Exercise
from app.repositories.exercise import ExerciseRepository


class ExerciseService:
    """Orchestrates exercise dictionary configuration and verifies schema formats."""

    def __init__(self, exercise_repo: ExerciseRepository | None = None):
        self.exercise_repo = exercise_repo or ExerciseRepository()

    def add_exercise(self, exercise: Exercise) -> str:
        """Validates configuration formatting and adds a new exercise to the system dictionary."""
        logger.info(f"Adding exercise to dictionary: {exercise.name}")

        # Validations
        if not exercise.name.strip():
            raise ValidationError("Exercise name cannot be empty.")

        if exercise.category not in ("strength", "cardio", "mobility"):
            raise ValidationError(message="Exercise category is invalid.", details=f"Category: {exercise.category}")

        # Confirm JSON formatting for form_rules and primary_muscles
        if exercise.primary_muscles:
            try:
                json.loads(exercise.primary_muscles)
            except ValueError:
                raise ValidationError("Primary muscles field must be a valid JSON list string.")

        try:
            json.loads(exercise.form_rules)
        except ValueError:
            raise ValidationError("Form rules field must be a valid JSON dictionary string.")

        # Ensure name uniqueness
        existing = self.exercise_repo.db.execute_read_one("SELECT 1 FROM exercises WHERE name = ?;", (exercise.name,))
        if existing:
            logger.warning(f"Registration rejected: Exercise name '{exercise.name}' already exists.")
            raise ValidationError(
                message="Exercise registration failed: Name already exists in catalog.",
                details=f"Name: {exercise.name}",
            )

        try:
            return self.exercise_repo.create_exercise(exercise)
        except Exception as e:
            logger.error(f"Failed to add exercise: {e!s}")
            raise ServiceError("Exercise registration failed.", details=str(e))

    def get_exercise(self, exercise_id: str) -> Exercise | None:
        """Retrieves a single exercise definition by ID."""
        return self.exercise_repo.get_exercise(exercise_id)

    def list_exercises(self) -> list[Exercise]:
        """Lists all exercise definitions in the catalog."""
        return self.exercise_repo.list_exercises()
