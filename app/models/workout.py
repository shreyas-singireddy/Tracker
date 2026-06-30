from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from enum import Enum


class TrainingSplit(str, Enum):
    PUSH = "Push"
    PULL = "Pull"
    LEGS = "Legs"
    FULL_BODY = "Full Body"
    UPPER = "Upper"
    LOWER = "Lower"


@dataclass
class WorkoutPlan:
    plan_id: str
    user_id: str
    name: str
    split_name: str  # Push, Pull, Legs, etc.
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkoutPlan":
        return cls(
            plan_id=data["plan_id"],
            user_id=data["user_id"],
            name=data["name"],
            split_name=data["split_name"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class WorkoutSession:
    session_id: str
    user_id: str
    plan_id: Optional[str]
    start_time: str
    end_time: Optional[str]
    status: str  # 'NOT_STARTED', 'ACTIVE', 'PAUSED', 'COMPLETED'
    calories_burned_kcal: float = 0.0
    avg_heart_rate: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkoutSession":
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            plan_id=data.get("plan_id"),
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            status=data["status"],
            calories_burned_kcal=float(data.get("calories_burned_kcal", 0.0)),
            avg_heart_rate=data.get("avg_heart_rate"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class ExerciseLog:
    exercise_log_id: str
    session_id: str
    exercise_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExerciseLog":
        return cls(
            exercise_log_id=data["exercise_log_id"],
            session_id=data["session_id"],
            exercise_id=data["exercise_id"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class ExerciseSet:
    set_id: str
    session_id: str
    exercise_log_id: str
    set_number: int
    weight: float
    reps: int
    rpe: Optional[float] = None  # Rate of Perceived Exertion
    is_completed: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # We need to manually handle boolean to integer translation for SQLite storage if using generic helpers,
        # but to_dict handles dict representation.
        d = asdict(self)
        d["is_completed"] = 1 if self.is_completed else 0
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExerciseSet":
        raw_completed = data.get("is_completed", False)
        # Handle SQLite integer boolean representation (0 or 1)
        is_completed = raw_completed in (1, True, "True", "1")
        return cls(
            set_id=data["set_id"],
            session_id=data["session_id"],
            exercise_log_id=data["exercise_log_id"],
            set_number=int(data["set_number"]),
            weight=float(data["weight"]),
            reps=int(data["reps"]),
            rpe=float(data["rpe"]) if data.get("rpe") is not None else None,
            is_completed=is_completed,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
