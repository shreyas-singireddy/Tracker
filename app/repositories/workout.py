from typing import Optional, List
from app.repositories.base import BaseRepository
from app.models.workout import WorkoutPlan, WorkoutSession, ExerciseLog, ExerciseSet


class WorkoutPlanRepository(BaseRepository):
    """Repository class managing CRUD operations for workout_plans."""

    def create_plan(self, plan: WorkoutPlan) -> str:
        """Saves a WorkoutPlan object to the database."""
        self.create("workout_plans", plan.to_dict())
        return plan.plan_id

    def get_plan(self, plan_id: str) -> Optional[WorkoutPlan]:
        """Fetches a WorkoutPlan object by ID."""
        row = self.read("workout_plans", "plan_id", plan_id)
        return WorkoutPlan.from_dict(row) if row else None

    def get_user_plans(self, user_id: str) -> List[WorkoutPlan]:
        """Retrieves all plans associated with a specific user."""
        query = "SELECT * FROM workout_plans WHERE user_id = ? ORDER BY created_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [WorkoutPlan.from_dict(row) for row in rows]

    def update_plan(self, plan_id: str, updates: dict) -> int:
        """Updates plan details."""
        return self.update("workout_plans", "plan_id", plan_id, updates)

    def delete_plan(self, plan_id: str) -> int:
        """Deletes a plan record."""
        return self.delete("workout_plans", "plan_id", plan_id)


class WorkoutSessionRepository(BaseRepository):
    """Repository class managing CRUD operations for workout_sessions."""

    def create_session(self, session: WorkoutSession) -> str:
        """Saves a WorkoutSession object to the database."""
        self.create("workout_sessions", session.to_dict())
        return session.session_id

    def get_session(self, session_id: str) -> Optional[WorkoutSession]:
        """Fetches a WorkoutSession object by ID."""
        row = self.read("workout_sessions", "session_id", session_id)
        return WorkoutSession.from_dict(row) if row else None

    def get_user_sessions(self, user_id: str) -> List[WorkoutSession]:
        """Retrieves all sessions registered to a specific user."""
        query = "SELECT * FROM workout_sessions WHERE user_id = ? ORDER BY start_time DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [WorkoutSession.from_dict(row) for row in rows]

    def get_active_session(self, user_id: str) -> Optional[WorkoutSession]:
        """Retrieves the current active (or paused) session for a specific user."""
        query = "SELECT * FROM workout_sessions WHERE user_id = ? AND status IN ('ACTIVE', 'PAUSED') LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id,))
        return WorkoutSession.from_dict(row) if row else None

    def update_session(self, session_id: str, updates: dict) -> int:
        """Updates session details."""
        return self.update("workout_sessions", "session_id", session_id, updates)

    def delete_session(self, session_id: str) -> int:
        """Deletes a session record."""
        return self.delete("workout_sessions", "session_id", session_id)


class ExerciseLogRepository(BaseRepository):
    """Repository class managing CRUD operations for exercise_logs."""

    def create_log(self, log: ExerciseLog) -> str:
        """Saves an ExerciseLog object to the database."""
        self.create("exercise_logs", log.to_dict())
        return log.exercise_log_id

    def get_log(self, exercise_log_id: str) -> Optional[ExerciseLog]:
        """Fetches an ExerciseLog object by ID."""
        row = self.read("exercise_logs", "exercise_log_id", exercise_log_id)
        return ExerciseLog.from_dict(row) if row else None

    def get_session_logs(self, session_id: str) -> List[ExerciseLog]:
        """Retrieves all exercise logs registered within a specific session."""
        query = "SELECT * FROM exercise_logs WHERE session_id = ? ORDER BY created_at ASC;"
        rows = self.db.execute_read(query, (session_id,))
        return [ExerciseLog.from_dict(row) for row in rows]

    def get_log_by_session_and_exercise(self, session_id: str, exercise_id: str) -> Optional[ExerciseLog]:
        """Retrieves an exercise log within a session by exercise_id."""
        query = "SELECT * FROM exercise_logs WHERE session_id = ? AND exercise_id = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (session_id, exercise_id))
        return ExerciseLog.from_dict(row) if row else None

    def delete_log(self, exercise_log_id: str) -> int:
        """Deletes an exercise log record."""
        return self.delete("exercise_logs", "exercise_log_id", exercise_log_id)


class ExerciseSetRepository(BaseRepository):
    """Repository class managing CRUD operations for exercise_sets."""

    def create_set(self, set_obj: ExerciseSet) -> str:
        """Saves an ExerciseSet object to the database."""
        self.create("exercise_sets", set_obj.to_dict())
        return set_obj.set_id

    def get_set(self, set_id: str) -> Optional[ExerciseSet]:
        """Fetches an ExerciseSet object by ID."""
        row = self.read("exercise_sets", "set_id", set_id)
        return ExerciseSet.from_dict(row) if row else None

    def get_session_sets(self, session_id: str) -> List[ExerciseSet]:
        """Retrieves all exercise sets associated with a specific session."""
        query = "SELECT * FROM exercise_sets WHERE session_id = ? ORDER BY set_number ASC;"
        rows = self.db.execute_read(query, (session_id,))
        return [ExerciseSet.from_dict(row) for row in rows]

    def get_log_sets(self, exercise_log_id: str) -> List[ExerciseSet]:
        """Retrieves all exercise sets grouped under a specific exercise log."""
        query = "SELECT * FROM exercise_sets WHERE exercise_log_id = ? ORDER BY set_number ASC;"
        rows = self.db.execute_read(query, (exercise_log_id,))
        return [ExerciseSet.from_dict(row) for row in rows]

    def get_duplicate_set(self, exercise_log_id: str, set_number: int) -> Optional[ExerciseSet]:
        """Finds if a set with the same set_number exists under the exercise log."""
        query = "SELECT * FROM exercise_sets WHERE exercise_log_id = ? AND set_number = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (exercise_log_id, set_number))
        return ExerciseSet.from_dict(row) if row else None

    def update_set(self, set_id: str, updates: dict) -> int:
        """Updates set details."""
        return self.update("exercise_sets", "set_id", set_id, updates)

    def delete_set(self, set_id: str) -> int:
        """Deletes a set record."""
        return self.delete("exercise_sets", "set_id", set_id)
