"""WorkoutModule standardization interface wrapper for FitOS (Sprint 10)."""
from typing import Dict, Any
from app.modules.base import BaseModule
from app.services.workout import WorkoutService
from app.repositories.workout import (
    WorkoutPlanRepository,
    WorkoutSessionRepository,
    ExerciseLogRepository,
    ExerciseSetRepository
)
from app.database.connection import db_manager

class WorkoutModule(BaseModule):
    """Encapsulates Workout domain logic interfaces."""

    def __init__(self):
        self.plan_repo = None
        self.session_repo = None
        self.log_repo = None
        self.set_repo = None
        self.service = None

    def init(self) -> None:
        """Initialise repositories and services."""
        self.plan_repo = WorkoutPlanRepository()
        self.session_repo = WorkoutSessionRepository()
        self.log_repo = ExerciseLogRepository()
        self.set_repo = ExerciseSetRepository()
        self.service = WorkoutService(
            plan_repo=self.plan_repo,
            session_repo=self.session_repo,
            log_repo=self.log_repo,
            set_repo=self.set_repo
        )

    def get_services(self) -> Dict[str, Any]:
        return {"WorkoutService": self.service}

    def get_repositories(self) -> Dict[str, Any]:
        return {
            "WorkoutPlanRepository": self.plan_repo,
            "WorkoutSessionRepository": self.session_repo,
            "ExerciseLogRepository": self.log_repo,
            "ExerciseSetRepository": self.set_repo
        }

    def health_check(self) -> Dict[str, Any]:
        """Verify we can access the database tables."""
        try:
            db_manager.execute_read("SELECT 1 FROM workout_plans LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM workout_sessions LIMIT 1;")
            return {"status": "GREEN", "details": "Workout module tables are readable and database connection is healthy."}
        except Exception as e:
            return {"status": "RED", "details": f"Workout health check failed: {str(e)}"}
