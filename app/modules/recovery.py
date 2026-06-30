"""RecoveryModule standardization interface wrapper for FitOS (Sprint 10)."""
from typing import Dict, Any
from app.modules.base import BaseModule
from app.services.recovery import RecoveryService
from app.repositories.sleep import SleepRepository
from app.repositories.recovery import RecoveryRepository, RecoveryProfileRepository
from app.database.connection import db_manager

class RecoveryModule(BaseModule):
    """Encapsulates Recovery domain logic interfaces."""

    def __init__(self):
        self.sleep_repo = None
        self.recovery_repo = None
        self.profile_repo = None
        self.service = None

    def init(self) -> None:
        self.sleep_repo = SleepRepository()
        self.recovery_repo = RecoveryRepository()
        self.profile_repo = RecoveryProfileRepository()
        self.service = RecoveryService(
            sleep_repo=self.sleep_repo,
            recovery_repo=self.recovery_repo,
            profile_repo=self.profile_repo
        )

    def get_services(self) -> Dict[str, Any]:
        return {"RecoveryService": self.service}

    def get_repositories(self) -> Dict[str, Any]:
        return {
            "SleepRepository": self.sleep_repo,
            "RecoveryRepository": self.recovery_repo,
            "RecoveryProfileRepository": self.profile_repo
        }

    def health_check(self) -> Dict[str, Any]:
        try:
            db_manager.execute_read("SELECT 1 FROM sleep_logs LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM recovery_logs LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM recovery_profiles LIMIT 1;")
            return {"status": "GREEN", "details": "Recovery module tables are readable."}
        except Exception as e:
            return {"status": "RED", "details": f"Recovery health check failed: {str(e)}"}
