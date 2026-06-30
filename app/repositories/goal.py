from typing import Optional, List
from app.repositories.base import BaseRepository
from app.models.domain import Goal


class GoalRepository(BaseRepository):
    """Repository class managing CRUD operations for the goals table."""

    def create_goal(self, goal: Goal) -> str:
        """Saves a Goal object to the database."""
        self.create("goals", goal.to_dict())
        return goal.goal_id

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Fetches a Goal object by its goal_id."""
        row = self.read("goals", "goal_id", goal_id)
        return Goal.from_dict(row) if row else None

    def get_user_goals(self, user_id: str) -> List[Goal]:
        """Retrieves all goals associated with a specific user."""
        query = "SELECT * FROM goals WHERE user_id = ?;"
        rows = self.db.execute_read(query, (user_id,))
        return [Goal.from_dict(row) for row in rows]

    def update_goal(self, goal_id: str, updates: dict) -> int:
        """Updates goal details."""
        return self.update("goals", "goal_id", goal_id, updates)

    def delete_goal(self, goal_id: str) -> int:
        """Deletes a goal record."""
        return self.delete("goals", "goal_id", goal_id)
