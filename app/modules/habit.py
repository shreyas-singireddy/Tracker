"""HabitModule standardization interface wrapper for FitOS (Sprint 10)."""
from typing import Dict, Any
from app.modules.base import BaseModule
from app.services.habit import HabitService
from app.repositories.habit import HabitRepository
from app.repositories.habit_log import HabitLogRepository
from app.database.connection import db_manager

class HabitModule(BaseModule):
    """Encapsulates Habit domain logic interfaces."""

    def __init__(self):
        self.habit_repo = None
        self.habit_log_repo = None
        self.service = None

    def init(self) -> None:
        self.habit_repo = HabitRepository()
        self.habit_log_repo = HabitLogRepository()
        self.service = HabitService(
            habit_repo=self.habit_repo,
            habit_log_repo=self.habit_log_repo
        )

    def get_services(self) -> Dict[str, Any]:
        return {"HabitService": self.service}

    def get_repositories(self) -> Dict[str, Any]:
        return {
            "HabitRepository": self.habit_repo,
            "HabitLogRepository": self.habit_log_repo
        }

    def health_check(self) -> Dict[str, Any]:
        try:
            db_manager.execute_read("SELECT 1 FROM habits LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM habit_entries LIMIT 1;")
            return {"status": "GREEN", "details": "Habit module tables are readable."}
        except Exception as e:
            return {"status": "RED", "details": f"Habit health check failed: {str(e)}"}
