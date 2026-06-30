"""AI Coach Repository Layer — Sprint 6.

Pure CRUD repositories for ai_sessions, ai_queries, ai_responses,
and ai_recommendations tables.  Zero business logic lives here.

All classes inherit BaseRepository from Sprint 2.
"""
from typing import List, Optional
from app.repositories.base import BaseRepository
from app.models.ai import AICoachSession, AIQuery, AIResponse, Recommendation


class AISessionRepository(BaseRepository):
    """CRUD for the ai_sessions table.

    Sessions group queries in a conversation.  Supports filtering by user_id.
    """

    def create_session(self, session: AICoachSession) -> str:
        """Persists a new AICoachSession.  Returns session_id."""
        self.create("ai_sessions", session.to_dict())
        return session.session_id

    def get_session(self, session_id: str) -> Optional[AICoachSession]:
        """Fetches a single session by primary key."""
        row = self.read("ai_sessions", "session_id", session_id)
        return AICoachSession.from_dict(row) if row else None

    def get_user_sessions(self, user_id: str) -> List[AICoachSession]:
        """Returns all sessions for a user, newest first."""
        query = "SELECT * FROM ai_sessions WHERE user_id = ? ORDER BY created_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [AICoachSession.from_dict(r) for r in rows]

    def update_session(self, session_id: str, updates: dict) -> int:
        """Updates session fields (e.g., ended_at, query_count)."""
        return self.update("ai_sessions", "session_id", session_id, updates)

    def delete_session(self, session_id: str) -> int:
        """Deletes a session and cascades to queries + responses."""
        return self.delete("ai_sessions", "session_id", session_id)

    def increment_query_count(self, session_id: str) -> int:
        """Atomically increments query_count for a session."""
        query = "UPDATE ai_sessions SET query_count = query_count + 1 WHERE session_id = ?;"
        return self.db.execute_write(query, (session_id,))


class AIQueryRepository(BaseRepository):
    """CRUD for the ai_queries table.

    Supports filtering by session_id, user_id, and intent category.
    """

    def create_query(self, ai_query: AIQuery) -> str:
        """Persists a new AIQuery.  Returns query_id."""
        self.create("ai_queries", ai_query.to_dict())
        return ai_query.query_id

    def get_query(self, query_id: str) -> Optional[AIQuery]:
        """Fetches a single query by primary key."""
        row = self.read("ai_queries", "query_id", query_id)
        return AIQuery.from_dict(row) if row else None

    def get_session_queries(self, session_id: str) -> List[AIQuery]:
        """Returns all queries within a session, chronological order."""
        query = "SELECT * FROM ai_queries WHERE session_id = ? ORDER BY created_at ASC;"
        rows = self.db.execute_read(query, (session_id,))
        return [AIQuery.from_dict(r) for r in rows]

    def get_user_queries(self, user_id: str) -> List[AIQuery]:
        """Returns all queries for a user, newest first."""
        query = "SELECT * FROM ai_queries WHERE user_id = ? ORDER BY created_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [AIQuery.from_dict(r) for r in rows]

    def get_queries_by_intent(self, user_id: str, intent: str) -> List[AIQuery]:
        """Returns all queries for a user with a specific intent classification."""
        query = "SELECT * FROM ai_queries WHERE user_id = ? AND intent = ? ORDER BY created_at DESC;"
        rows = self.db.execute_read(query, (user_id, intent))
        return [AIQuery.from_dict(r) for r in rows]

    def delete_query(self, query_id: str) -> int:
        """Deletes a query (cascades to its response)."""
        return self.delete("ai_queries", "query_id", query_id)


class AIResponseRepository(BaseRepository):
    """CRUD for the ai_responses table.

    Every response has a mandatory rule_source (explainability contract).
    Supports filtering by query_id and user_id.
    """

    def create_response(self, response: AIResponse) -> str:
        """Persists a new AIResponse.  Returns response_id."""
        self.create("ai_responses", response.to_dict())
        return response.response_id

    def get_response(self, response_id: str) -> Optional[AIResponse]:
        """Fetches a single response by primary key."""
        row = self.read("ai_responses", "response_id", response_id)
        return AIResponse.from_dict(row) if row else None

    def get_response_for_query(self, query_id: str) -> Optional[AIResponse]:
        """Returns the response for a specific query (1-to-1 relationship)."""
        query = "SELECT * FROM ai_responses WHERE query_id = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (query_id,))
        return AIResponse.from_dict(row) if row else None

    def get_user_responses(self, user_id: str) -> List[AIResponse]:
        """Returns all responses for a user, newest first."""
        query = "SELECT * FROM ai_responses WHERE user_id = ? ORDER BY created_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [AIResponse.from_dict(r) for r in rows]

    def delete_response(self, response_id: str) -> int:
        """Deletes a single response."""
        return self.delete("ai_responses", "response_id", response_id)


class AIRecommendationRepository(BaseRepository):
    """CRUD for the ai_recommendations table.

    Every recommendation has a mandatory rule_source (explainability contract).
    Supports filtering by user_id, category, priority, and log_date.
    """

    def create_recommendation(self, rec: Recommendation) -> str:
        """Persists a new Recommendation.  Returns recommendation_id."""
        self.create("ai_recommendations", rec.to_dict())
        return rec.recommendation_id

    def get_recommendation(self, recommendation_id: str) -> Optional[Recommendation]:
        """Fetches a single recommendation by primary key."""
        row = self.read("ai_recommendations", "recommendation_id", recommendation_id)
        return Recommendation.from_dict(row) if row else None

    def get_user_recommendations(self, user_id: str) -> List[Recommendation]:
        """Returns all recommendations for a user, newest first."""
        query = "SELECT * FROM ai_recommendations WHERE user_id = ? ORDER BY created_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [Recommendation.from_dict(r) for r in rows]

    def get_recommendations_by_category(self, user_id: str, category: str) -> List[Recommendation]:
        """Returns recommendations filtered by domain category."""
        query = (
            "SELECT * FROM ai_recommendations "
            "WHERE user_id = ? AND category = ? ORDER BY created_at DESC;"
        )
        rows = self.db.execute_read(query, (user_id, category))
        return [Recommendation.from_dict(r) for r in rows]

    def get_recommendations_by_date(self, user_id: str, log_date: str) -> List[Recommendation]:
        """Returns recommendations generated for a specific date context."""
        query = (
            "SELECT * FROM ai_recommendations "
            "WHERE user_id = ? AND log_date = ? ORDER BY priority ASC, created_at DESC;"
        )
        rows = self.db.execute_read(query, (user_id, log_date))
        return [Recommendation.from_dict(r) for r in rows]

    def get_high_priority(self, user_id: str) -> List[Recommendation]:
        """Returns only high-priority recommendations for a user."""
        query = (
            "SELECT * FROM ai_recommendations "
            "WHERE user_id = ? AND priority = 'high' ORDER BY created_at DESC;"
        )
        rows = self.db.execute_read(query, (user_id,))
        return [Recommendation.from_dict(r) for r in rows]

    def delete_recommendation(self, recommendation_id: str) -> int:
        """Deletes a recommendation."""
        return self.delete("ai_recommendations", "recommendation_id", recommendation_id)

    def delete_user_recommendations_by_date(self, user_id: str, log_date: str) -> int:
        """Removes all recommendations for a user on a specific date (for re-generation)."""
        query = "DELETE FROM ai_recommendations WHERE user_id = ? AND log_date = ?;"
        return self.db.execute_write(query, (user_id, log_date))
