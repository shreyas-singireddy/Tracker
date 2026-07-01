"""AI Coach Domain Models — Sprint 6.

All models are typed dataclasses.  They are serializable via to_dict() / from_dict()
and contain NO business logic (validation and intelligence live in AICoachService).
"""

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------


class IntentCategory(StrEnum):
    """Rule-based NLP intent categories understood by the AI Coach."""

    NUTRITION_QUERY = "nutrition_query"
    WORKOUT_QUERY = "workout_query"
    RECOVERY_QUERY = "recovery_query"
    HABIT_QUERY = "habit_query"
    PROGRESS_QUERY = "progress_query"
    GENERAL_FITNESS_QUERY = "general_fitness_query"


class RecommendationPriority(StrEnum):
    """Priority tiers for AI recommendations."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationCategory(StrEnum):
    """Domain categories for recommendations."""

    NUTRITION = "nutrition"
    WORKOUT = "workout"
    RECOVERY = "recovery"
    HABIT = "habit"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# Persisted models (stored in ai_* tables)
# ---------------------------------------------------------------------------


@dataclass
class AICoachSession:
    """A conversation session grouping one or more queries from the same user.

    Persisted in ai_sessions table.
    """

    session_id: str
    user_id: str
    started_at: str | None = None
    ended_at: str | None = None
    query_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AICoachSession":
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            query_count=int(data.get("query_count", 0)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class AIQuery:
    """A single user question submitted to the AI Coach.

    Every query has a classified intent (resolved by the NLP engine) and is
    linked to an AICoachSession.  Persisted in ai_queries table.
    """

    query_id: str
    session_id: str
    user_id: str
    raw_text: str
    intent: str  # IntentCategory value
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AIQuery":
        return cls(
            query_id=data["query_id"],
            session_id=data["session_id"],
            user_id=data["user_id"],
            raw_text=data["raw_text"],
            intent=data["intent"],
            created_at=data.get("created_at"),
        )


@dataclass
class AIResponse:
    """The AI Coach's response to an AIQuery.

    CRITICAL: Every response MUST have a non-empty `rule_source` that names
    the exact rule(s) that produced the response text.  This enforces
    full explainability — no hallucinated content is possible.

    Persisted in ai_responses table.
    """

    response_id: str
    query_id: str
    user_id: str
    response_text: str
    intent: str  # mirrors the query's intent
    rule_source: str  # mandatory — e.g. "Rule: recovery_score < 40 → rest day"
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AIResponse":
        return cls(
            response_id=data["response_id"],
            query_id=data["query_id"],
            user_id=data["user_id"],
            response_text=data["response_text"],
            intent=data["intent"],
            rule_source=data["rule_source"],
            created_at=data.get("created_at"),
        )


@dataclass
class Recommendation:
    """A single actionable recommendation produced by the AI Coach.

    Every recommendation MUST have a non-empty `rule_source` string so the
    user and developer can trace exactly which rule triggered it.

    Persisted in ai_recommendations table.
    """

    recommendation_id: str
    user_id: str
    category: str  # RecommendationCategory value
    title: str
    body: str
    rule_source: str  # mandatory — references named rule constant
    priority: str = RecommendationPriority.MEDIUM.value
    log_date: str | None = None  # date context used for generation
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Recommendation":
        return cls(
            recommendation_id=data["recommendation_id"],
            user_id=data["user_id"],
            category=data["category"],
            title=data["title"],
            body=data["body"],
            rule_source=data["rule_source"],
            priority=data.get("priority", RecommendationPriority.MEDIUM.value),
            log_date=data.get("log_date"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


# ---------------------------------------------------------------------------
# In-memory rule registry (NOT persisted)
# ---------------------------------------------------------------------------


@dataclass
class InsightRule:
    """Defines a single rule used by the AI recommendation engine.

    InsightRules live as code constants in AICoachService — they are NEVER
    stored in the database.  This keeps the logic auditable and version-controlled.
    """

    rule_id: str  # unique constant name, e.g. "RULE_LOW_RECOVERY"
    category: str  # RecommendationCategory value
    condition: str  # human-readable description of the trigger condition
    message: str  # response message template

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
