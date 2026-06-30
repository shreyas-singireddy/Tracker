from typing import Optional, List
from app.repositories.base import BaseRepository
from app.models.domain import Exercise


class ExerciseRepository(BaseRepository):
    """Repository class managing CRUD operations for the exercises table."""

    def create_exercise(self, exercise: Exercise) -> str:
        """Saves an Exercise object to the database."""
        self.create("exercises", exercise.to_dict())
        return exercise.exercise_id

    def get_exercise(self, exercise_id: str) -> Optional[Exercise]:
        """Fetches an Exercise object by its exercise_id."""
        row = self.read("exercises", "exercise_id", exercise_id)
        return Exercise.from_dict(row) if row else None

    def update_exercise(self, exercise_id: str, updates: dict) -> int:
        """Updates exercise details."""
        return self.update("exercises", "exercise_id", exercise_id, updates)

    def delete_exercise(self, exercise_id: str) -> int:
        """Deletes an exercise record."""
        return self.delete("exercises", "exercise_id", exercise_id)

    def list_exercises(self) -> List[Exercise]:
        """Lists all exercises."""
        rows = self.list_all("exercises")
        return [Exercise.from_dict(row) for row in rows]
