from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class User:
    user_id: str
    name: str
    email: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            user_id=data["user_id"],
            name=data["name"],
            email=data["email"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class UserProfile:
    user_id: str
    birth_date: str
    weight_kg: float
    height_cm: float
    resting_hr: Optional[int] = None
    max_hr: Optional[int] = None
    fitness_level: Optional[str] = None  # 'beginner', 'intermediate', 'advanced'
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        return cls(
            user_id=data["user_id"],
            birth_date=data["birth_date"],
            weight_kg=float(data["weight_kg"]),
            height_cm=float(data["height_cm"]),
            resting_hr=data.get("resting_hr"),
            max_hr=data.get("max_hr"),
            fitness_level=data.get("fitness_level"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class Goal:
    goal_id: str
    user_id: str
    category: str  # 'weight', 'steps', 'calories', 'water', 'sleep'
    target_value: float
    current_value: float = 0.0
    start_date: str = ""
    target_date: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        return cls(
            goal_id=data["goal_id"],
            user_id=data["user_id"],
            category=data["category"],
            target_value=float(data["target_value"]),
            current_value=float(data.get("current_value", 0.0)),
            start_date=data.get("start_date", ""),
            target_date=data.get("target_date"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class FoodItem:
    food_id: str
    name: str
    calories: float
    protein: float = 0.0
    carbs: float = 0.0
    fats: float = 0.0
    serving_size_g: float = 100.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FoodItem":
        return cls(
            food_id=data["food_id"],
            name=data["name"],
            calories=float(data["calories"]),
            protein=float(data.get("protein", 0.0)),
            carbs=float(data.get("carbs", 0.0)),
            fats=float(data.get("fats", 0.0)),
            serving_size_g=float(data.get("serving_size_g", 100.0)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class Exercise:
    exercise_id: str
    name: str
    category: str  # 'strength', 'cardio', 'mobility'
    primary_muscles: Optional[str] = None  # JSON string
    form_rules: str = ""  # JSON string
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Exercise":
        return cls(
            exercise_id=data["exercise_id"],
            name=data["name"],
            category=data["category"],
            primary_muscles=data.get("primary_muscles"),
            form_rules=data.get("form_rules", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class MealLog:
    meal_log_id: str
    user_id: str
    food_id: str
    serving_multiplier: float = 1.0
    logged_at: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MealLog":
        return cls(
            meal_log_id=data["meal_log_id"],
            user_id=data["user_id"],
            food_id=data["food_id"],
            serving_multiplier=float(data.get("serving_multiplier", 1.0)),
            logged_at=data["logged_at"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class WorkoutLog:
    log_id: str
    user_id: str
    exercise_id: str
    set_number: int
    completed_reps: int
    target_reps: Optional[int] = None
    average_velocity: Optional[float] = None
    form_score: Optional[float] = None
    logged_at: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkoutLog":
        return cls(
            log_id=data["log_id"],
            user_id=data["user_id"],
            exercise_id=data["exercise_id"],
            set_number=int(data["set_number"]),
            completed_reps=int(data["completed_reps"]),
            target_reps=data.get("target_reps"),
            average_velocity=data.get("average_velocity"),
            form_score=data.get("form_score"),
            logged_at=data.get("logged_at", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class HabitLog:
    habit_log_id: str
    habit_id: str
    user_id: str
    log_date: str  # YYYY-MM-DD
    value: float = 1.0
    status: str = "completed"  # 'completed', 'missed', 'partial'
    note: str = ""
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HabitLog":
        return cls(
            habit_log_id=data["habit_log_id"],
            habit_id=data["habit_id"],
            user_id=data["user_id"],
            log_date=data["log_date"],
            value=float(data.get("value", 1.0)),
            status=data.get("status", "completed"),
            note=data.get("note", ""),
            created_at=data.get("created_at")
        )


@dataclass
class BodyMeasurement:
    measurement_id: str
    user_id: str
    weight_kg: float
    logged_at: str
    body_fat_percentage: Optional[float] = None
    chest_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hips_cm: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BodyMeasurement":
        return cls(
            measurement_id=data["measurement_id"],
            user_id=data["user_id"],
            weight_kg=float(data["weight_kg"]),
            body_fat_percentage=data.get("body_fat_percentage"),
            chest_cm=data.get("chest_cm"),
            waist_cm=data.get("waist_cm"),
            hips_cm=data.get("hips_cm"),
            logged_at=data["logged_at"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
