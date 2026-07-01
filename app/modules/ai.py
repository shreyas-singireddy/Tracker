"""AIModule standardization interface wrapper for FitOS (Sprint 10)."""

from typing import Any

from app.database.connection import db_manager
from app.modules.base import BaseModule
from app.repositories.ai import AIQueryRepository, AIRecommendationRepository, AIResponseRepository, AISessionRepository
from app.services.ai_coach import AICoachService


class AIModule(BaseModule):
    """Encapsulates AI Coach domain logic interfaces."""

    def __init__(self):
        self.session_repo = None
        self.query_repo = None
        self.response_repo = None
        self.rec_repo = None
        self.service = None

    def init(self) -> None:
        self.session_repo = AISessionRepository()
        self.query_repo = AIQueryRepository()
        self.response_repo = AIResponseRepository()
        self.rec_repo = AIRecommendationRepository()
        self.service = AICoachService(
            session_repo=self.session_repo,
            query_repo=self.query_repo,
            response_repo=self.response_repo,
            rec_repo=self.rec_repo,
        )

    def get_services(self) -> dict[str, Any]:
        return {"AICoachService": self.service}

    def get_repositories(self) -> dict[str, Any]:
        return {
            "AISessionRepository": self.session_repo,
            "AIQueryRepository": self.query_repo,
            "AIResponseRepository": self.response_repo,
            "AIRecommendationRepository": self.rec_repo,
        }

    def health_check(self) -> dict[str, Any]:
        try:
            db_manager.execute_read("SELECT 1 FROM ai_sessions LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM ai_queries LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM ai_responses LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM ai_recommendations LIMIT 1;")
            return {"status": "GREEN", "details": "AI module tables are readable."}
        except Exception as e:
            return {"status": "RED", "details": f"AI health check failed: {e!s}"}
