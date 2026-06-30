"""AnalyticsModule standardization interface wrapper for FitOS (Sprint 10)."""
from typing import Dict, Any
from app.modules.base import BaseModule
from app.services.analytics import AnalyticsService
from app.repositories.analytics import (
    FitnessScoreRepository,
    ReportRepository,
    AnalyticsSnapshotRepository,
    ProgressTrendRepository
)
from app.database.connection import db_manager

class AnalyticsModule(BaseModule):
    """Encapsulates Analytics domain logic interfaces."""

    def __init__(self):
        self.score_repo = None
        self.report_repo = None
        self.snapshot_repo = None
        self.trend_repo = None
        self.service = None

    def init(self) -> None:
        self.score_repo = FitnessScoreRepository()
        self.report_repo = ReportRepository()
        self.snapshot_repo = AnalyticsSnapshotRepository()
        self.trend_repo = ProgressTrendRepository()
        self.service = AnalyticsService(
            score_repo=self.score_repo,
            report_repo=self.report_repo,
            snapshot_repo=self.snapshot_repo,
            trend_repo=self.trend_repo
        )

    def get_services(self) -> Dict[str, Any]:
        return {"AnalyticsService": self.service}

    def get_repositories(self) -> Dict[str, Any]:
        return {
            "FitnessScoreRepository": self.score_repo,
            "ReportRepository": self.report_repo,
            "AnalyticsSnapshotRepository": self.snapshot_repo,
            "ProgressTrendRepository": self.trend_repo
        }

    def health_check(self) -> Dict[str, Any]:
        try:
            db_manager.execute_read("SELECT 1 FROM fitness_scores LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM weekly_reports LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM monthly_reports LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM analytics_snapshots LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM progress_trends LIMIT 1;")
            return {"status": "GREEN", "details": "Analytics module tables are readable."}
        except Exception as e:
            return {"status": "RED", "details": f"Analytics health check failed: {str(e)}"}
