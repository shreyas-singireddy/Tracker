from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ReadinessState(StrEnum):
    FULL = "FULL"
    MODERATE = "MODERATE"
    LOW = "LOW"


class HabitFrequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class Habit:
    habit_id: str
    user_id: str
    name: str
    description: str = ""
    frequency: str = "daily"  # 'daily', 'weekly'
    target_value: float = 1.0
    unit: str = "times"  # 'times', 'minutes', 'cups', etc.
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Habit":
        return cls(
            habit_id=data["habit_id"],
            user_id=data["user_id"],
            name=data["name"],
            description=data.get("description", ""),
            frequency=data.get("frequency", "daily"),
            target_value=float(data.get("target_value", 1.0)),
            unit=data.get("unit", "times"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class SleepLog:
    sleep_log_id: str
    user_id: str
    log_date: str  # YYYY-MM-DD
    hours: float  # 0-24
    quality_score: float  # 0-10
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SleepLog":
        return cls(
            sleep_log_id=data["sleep_log_id"],
            user_id=data["user_id"],
            log_date=data["log_date"],
            hours=float(data["hours"]),
            quality_score=float(data["quality_score"]),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class RecoveryLog:
    recovery_log_id: str
    user_id: str
    log_date: str  # YYYY-MM-DD
    recovery_score: float  # 0-100
    readiness_state: str  # 'FULL', 'MODERATE', 'LOW'
    sleep_quality_component: float = 0.0
    sleep_duration_component: float = 0.0
    workout_load_component: float = 0.0
    rest_days_component: float = 0.0
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecoveryLog":
        return cls(
            recovery_log_id=data["recovery_log_id"],
            user_id=data["user_id"],
            log_date=data["log_date"],
            recovery_score=float(data["recovery_score"]),
            readiness_state=data["readiness_state"],
            sleep_quality_component=float(data.get("sleep_quality_component", 0.0)),
            sleep_duration_component=float(data.get("sleep_duration_component", 0.0)),
            workout_load_component=float(data.get("workout_load_component", 0.0)),
            rest_days_component=float(data.get("rest_days_component", 0.0)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class RecoveryProfile:
    profile_id: str
    user_id: str
    baseline_sleep_hours: float = 8.0
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecoveryProfile":
        return cls(
            profile_id=data["profile_id"],
            user_id=data["user_id"],
            baseline_sleep_hours=float(data.get("baseline_sleep_hours", 8.0)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
