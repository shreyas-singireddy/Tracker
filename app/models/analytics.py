from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class FitnessScore:
    score_id: str
    user_id: str
    log_date: str  # YYYY-MM-DD
    overall_score: float  # 0-100
    nutrition_score: float = 0.0
    workout_consistency_score: float = 0.0
    progressive_overload_score: float = 0.0
    recovery_score: float = 0.0
    habits_score: float = 0.0
    body_progress_score: float = 0.0
    ai_adherence_score: float = 0.0
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FitnessScore":
        return cls(
            score_id=data["score_id"],
            user_id=data["user_id"],
            log_date=data["log_date"],
            overall_score=float(data["overall_score"]),
            nutrition_score=float(data.get("nutrition_score", 0.0)),
            workout_consistency_score=float(data.get("workout_consistency_score", 0.0)),
            progressive_overload_score=float(data.get("progressive_overload_score", 0.0)),
            recovery_score=float(data.get("recovery_score", 0.0)),
            habits_score=float(data.get("habits_score", 0.0)),
            body_progress_score=float(data.get("body_progress_score", 0.0)),
            ai_adherence_score=float(data.get("ai_adherence_score", 0.0)),
            created_at=data.get("created_at"),
        )


@dataclass
class WeeklyReport:
    report_id: str
    user_id: str
    week_start: str  # YYYY-MM-DD
    week_end: str  # YYYY-MM-DD
    total_workouts: int = 0
    avg_calories: float = 0.0
    avg_protein_g: float = 0.0
    avg_recovery_score: float = 0.0
    habit_streaks_best: int = 0
    avg_fitness_score: float = 0.0
    adherence_rate: float = 0.0
    insight_summary: str = ""
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WeeklyReport":
        return cls(
            report_id=data["report_id"],
            user_id=data["user_id"],
            week_start=data["week_start"],
            week_end=data["week_end"],
            total_workouts=int(data.get("total_workouts", 0)),
            avg_calories=float(data.get("avg_calories", 0.0)),
            avg_protein_g=float(data.get("avg_protein_g", 0.0)),
            avg_recovery_score=float(data.get("avg_recovery_score", 0.0)),
            habit_streaks_best=int(data.get("habit_streaks_best", 0)),
            avg_fitness_score=float(data.get("avg_fitness_score", 0.0)),
            adherence_rate=float(data.get("adherence_rate", 0.0)),
            insight_summary=data.get("insight_summary", ""),
            created_at=data.get("created_at"),
        )


@dataclass
class MonthlyReport:
    report_id: str
    user_id: str
    month_start: str  # YYYY-MM-DD
    month_end: str  # YYYY-MM-DD
    total_workouts: int = 0
    avg_calories: float = 0.0
    avg_protein_g: float = 0.0
    avg_recovery_score: float = 0.0
    avg_fitness_score: float = 0.0
    adherence_rate: float = 0.0
    strength_improvements: str = ""
    body_changes_summary: str = ""
    progress_summary: str = ""
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MonthlyReport":
        return cls(
            report_id=data["report_id"],
            user_id=data["user_id"],
            month_start=data["month_start"],
            month_end=data["month_end"],
            total_workouts=int(data.get("total_workouts", 0)),
            avg_calories=float(data.get("avg_calories", 0.0)),
            avg_protein_g=float(data.get("avg_protein_g", 0.0)),
            avg_recovery_score=float(data.get("avg_recovery_score", 0.0)),
            avg_fitness_score=float(data.get("avg_fitness_score", 0.0)),
            adherence_rate=float(data.get("adherence_rate", 0.0)),
            strength_improvements=data.get("strength_improvements", ""),
            body_changes_summary=data.get("body_changes_summary", ""),
            progress_summary=data.get("progress_summary", ""),
            created_at=data.get("created_at"),
        )


@dataclass
class AnalyticsSnapshot:
    snapshot_id: str
    user_id: str
    snapshot_date: str
    fitness_score: float = 0.0
    total_workouts_ytd: int = 0
    current_streak_best: int = 0
    nutrition_compliance_rate: float = 0.0
    recovery_avg_7day: float = 0.0
    body_weight_kg: float | None = None
    snapshot_data: str = ""  # JSON string for extensibility
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalyticsSnapshot":
        return cls(
            snapshot_id=data["snapshot_id"],
            user_id=data["user_id"],
            snapshot_date=data["snapshot_date"],
            fitness_score=float(data.get("fitness_score", 0.0)),
            total_workouts_ytd=int(data.get("total_workouts_ytd", 0)),
            current_streak_best=int(data.get("current_streak_best", 0)),
            nutrition_compliance_rate=float(data.get("nutrition_compliance_rate", 0.0)),
            recovery_avg_7day=float(data.get("recovery_avg_7day", 0.0)),
            body_weight_kg=float(data["body_weight_kg"]) if data.get("body_weight_kg") is not None else None,
            snapshot_data=data.get("snapshot_data", ""),
            created_at=data.get("created_at"),
        )


@dataclass
class ProgressTrend:
    trend_id: str
    user_id: str
    metric_name: str  # 'weight', 'strength', 'consistency', 'recovery', 'nutrition_stability'
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    current_value: float = 0.0
    previous_value: float = 0.0
    delta_value: float = 0.0
    percentage_change: float = 0.0
    moving_avg_7day: float = 0.0
    moving_avg_30day: float = 0.0
    period_start: str = ""
    period_end: str = ""
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProgressTrend":
        return cls(
            trend_id=data["trend_id"],
            user_id=data["user_id"],
            metric_name=data["metric_name"],
            trend_direction=data["trend_direction"],
            current_value=float(data.get("current_value", 0.0)),
            previous_value=float(data.get("previous_value", 0.0)),
            delta_value=float(data.get("delta_value", 0.0)),
            percentage_change=float(data.get("percentage_change", 0.0)),
            moving_avg_7day=float(data.get("moving_avg_7day", 0.0)),
            moving_avg_30day=float(data.get("moving_avg_30day", 0.0)),
            period_start=data.get("period_start", ""),
            period_end=data.get("period_end", ""),
            created_at=data.get("created_at"),
        )


@dataclass
class InsightMetric:
    """A single computed insight for a user."""

    insight_id: str
    user_id: str
    category: str  # 'nutrition', 'workout', 'recovery', 'habits', 'general'
    metric_name: str  # e.g., 'protein_below_target', 'recovery_improved'
    current_value: float = 0.0
    previous_value: float = 0.0
    message: str = ""
    severity: str = "info"  # 'positive', 'warning', 'info'
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InsightMetric":
        return cls(
            insight_id=data["insight_id"],
            user_id=data["user_id"],
            category=data["category"],
            metric_name=data["metric_name"],
            current_value=float(data.get("current_value", 0.0)),
            previous_value=float(data.get("previous_value", 0.0)),
            message=data.get("message", ""),
            severity=data.get("severity", "info"),
            created_at=data.get("created_at"),
        )
